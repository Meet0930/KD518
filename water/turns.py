from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import BottleFillEntry, PendingTask, Roommate, SkipTurn, TurnState
from .notifications import send_turn_reminder_email


@dataclass
class TurnResult:
    entry: BottleFillEntry
    current_turn: Roommate | None
    next_turn: Roommate | None
    remaining_bottles: int | None
    messages: list[str]


def _apply_pending_task(roommate: Roommate, quantity: int, messages: list[str]) -> None:
    pending = (
        PendingTask.objects.filter(roommate=roommate, is_completed=False)
        .order_by("-updated_at")
        .first()
    )
    if not pending:
        if quantity == 1:
            PendingTask.objects.create(roommate=roommate, remaining_bottles=1)
            messages.append(f"{roommate.name} filled 1 bottle (1 remaining for {roommate.name}).")
        else:
            messages.append(f"{roommate.name} completed an extra contribution of 2 bottles.")
        return

    if quantity >= pending.remaining_bottles:
        previous_remaining = pending.remaining_bottles
        pending.is_completed = True
        pending.remaining_bottles = 1
        pending.save(update_fields=["is_completed", "remaining_bottles", "updated_at"])
        messages.append(f"{roommate.name}'s pending task is completed.")
        extra = quantity - previous_remaining
        if extra == 1:
            PendingTask.objects.create(roommate=roommate, remaining_bottles=1)
            messages.append(f"{roommate.name} filled 1 extra bottle (1 remaining for {roommate.name}).")
    else:
        pending.remaining_bottles -= quantity
        pending.save(update_fields=["remaining_bottles", "updated_at"])
        messages.append(
            f"{roommate.name} filled {quantity} bottle(s) ({pending.remaining_bottles} remaining for {roommate.name})."
        )


def _apply_pending_task_replay(pending_map: dict[int, int], roommate_id: int, quantity: int) -> None:
    current_remaining = pending_map.get(roommate_id, 0)
    if current_remaining <= 0:
        if quantity == 1:
            pending_map[roommate_id] = 1
        return
    new_remaining = current_remaining - quantity
    if new_remaining <= 0:
        pending_map.pop(roommate_id, None)
        if new_remaining < 0:
            pending_map[roommate_id] = 1
    else:
        pending_map[roommate_id] = new_remaining


def _ordered_roommates():
    return list(Roommate.objects.all().order_by("turn_position", "id"))


def _get_next_in_rotation(current: Roommate | None, roommates: list[Roommate]) -> Roommate | None:
    if not roommates:
        return None
    if current is None:
        return roommates[0]
    for idx, rm in enumerate(roommates):
        if rm.id == current.id:
            return roommates[(idx + 1) % len(roommates)]
    return roommates[0]


def _consume_skip_if_any(roommate: Roommate) -> bool:
    skip = SkipTurn.objects.filter(roommate=roommate, is_used=False).order_by("created_at").first()
    if not skip:
        return False
    skip.is_used = True
    skip.used_at = timezone.now()
    skip.save(update_fields=["is_used", "used_at"])
    return True


def _next_effective_turn(current: Roommate | None, roommates: list[Roommate], messages: list[str]) -> Roommate | None:
    if not roommates:
        return None
    candidate = _get_next_in_rotation(current, roommates)
    checked = 0
    while candidate and checked < len(roommates):
        if _consume_skip_if_any(candidate):
            messages.append(f"{candidate.name}'s own turn was skipped due to over-contribution.")
            candidate = _get_next_in_rotation(candidate, roommates)
            checked += 1
            continue
        return candidate
    return candidate


def get_turn_snapshot() -> dict:
    roommates = _ordered_roommates()
    turn_state = TurnState.get_solo()
    current = turn_state.current_roommate
    if current is None and roommates:
        current = roommates[0]
        turn_state.current_roommate = current
        turn_state.remaining_bottles = 2
        turn_state.save(update_fields=["current_roommate", "remaining_bottles", "updated_at"])

    pending_tasks = PendingTask.objects.filter(is_completed=False).select_related("roommate")
    first_pending = pending_tasks.first()
    focus_actor_text = ""
    if first_pending:
        bottle_word = "bottle" if first_pending.remaining_bottles == 1 else "bottles"
        focus_actor_text = (
            f"Pending: {first_pending.roommate.name} "
            f"({first_pending.remaining_bottles} {bottle_word} remaining)"
        )
    elif current:
        focus_actor_text = f"Current Turn: {current.name}"

    return {
        "current_turn": current,
        "next_turn": _get_next_in_rotation(current, roommates) if current else None,
        "remaining_bottles": turn_state.remaining_bottles if current else None,
        "pending_tasks": pending_tasks,
        "pending_user": first_pending.roommate if first_pending else None,
        "focus_actor_text": focus_actor_text,
    }


@transaction.atomic
def rebuild_turn_state_from_entries() -> None:
    roommates = _ordered_roommates()
    turn_state = TurnState.get_solo()

    PendingTask.objects.all().delete()
    SkipTurn.objects.all().delete()

    if not roommates:
        turn_state.current_roommate = None
        turn_state.remaining_bottles = 2
        turn_state.save(update_fields=["current_roommate", "remaining_bottles", "updated_at"])
        return

    current = roommates[0]
    remaining = 2
    pending_map: dict[int, int] = {}
    skip_counts: dict[int, int] = {}

    def get_next_in_rotation_local(current_roommate: Roommate | None) -> Roommate | None:
        return _get_next_in_rotation(current_roommate, roommates)

    def next_effective_local(current_roommate: Roommate | None) -> Roommate | None:
        candidate = get_next_in_rotation_local(current_roommate)
        checked = 0
        while candidate and checked < len(roommates):
            count = skip_counts.get(candidate.id, 0)
            if count > 0:
                skip_counts[candidate.id] = count - 1
                if skip_counts[candidate.id] <= 0:
                    skip_counts.pop(candidate.id, None)
                candidate = get_next_in_rotation_local(candidate)
                checked += 1
                continue
            return candidate
        return candidate

    entries = BottleFillEntry.objects.select_related("roommate", "target_roommate").order_by(
        "filled_at", "id"
    )
    for entry in entries:
        actor = entry.roommate
        if not actor:
            continue
        if actor.id == current.id:
            qty = min(entry.quantity, remaining)
            remaining -= qty
            if remaining <= 0:
                current = next_effective_local(current) or current
                remaining = 2
            continue

        if entry.action_type == BottleFillEntry.ACTION_PARTIAL_HELP:
            remaining = max(1, remaining - 1)
            _apply_pending_task_replay(pending_map, actor.id, 1)
            continue

        if entry.action_type == BottleFillEntry.ACTION_FULL_HELP_SKIP:
            skip_counts[actor.id] = skip_counts.get(actor.id, 0) + 1
            current = next_effective_local(current) or current
            remaining = 2
            continue

        # Fallback for legacy entries by non-current users.
        remaining = max(1, remaining - min(entry.quantity, 2))
        _apply_pending_task_replay(pending_map, actor.id, min(entry.quantity, 2))

    turn_state.current_roommate = current
    turn_state.remaining_bottles = remaining
    turn_state.save(update_fields=["current_roommate", "remaining_bottles", "updated_at"])

    for roommate_id, pending_remaining in pending_map.items():
        if pending_remaining > 0:
            PendingTask.objects.create(
                roommate_id=roommate_id,
                remaining_bottles=min(max(pending_remaining, 1), 2),
                is_completed=False,
            )

    for roommate_id, count in skip_counts.items():
        for _ in range(count):
            SkipTurn.objects.create(roommate_id=roommate_id, reason="full_help_skip", is_used=False)


@transaction.atomic
def record_turn_fill(*, actor: Roommate, quantity: int) -> TurnResult:
    if quantity not in (1, 2):
        raise ValidationError("Quantity must be 1 or 2.")

    roommates = _ordered_roommates()
    if not roommates:
        raise ValidationError("No roommates configured.")

    turn_state = TurnState.get_solo()
    if turn_state.current_roommate is None:
        turn_state.current_roommate = roommates[0]
        turn_state.remaining_bottles = 2

    current = turn_state.current_roommate
    assert current is not None

    messages: list[str] = []
    action_type = BottleFillEntry.ACTION_NORMAL

    if actor.id != current.id:
        if quantity == 1:
            action_type = BottleFillEntry.ACTION_PARTIAL_HELP
            turn_state.remaining_bottles = max(1, turn_state.remaining_bottles - 1)
            _apply_pending_task(actor, 1, messages)
            messages.append(f"{actor.name} helped {current.name} (1 bottle).")
            messages.append(
                f"{current.name} still needs to complete {turn_state.remaining_bottles} bottle."
            )
            entry = BottleFillEntry.objects.create(
                roommate=actor,
                target_roommate=current,
                quantity=1,
                action_type=action_type,
            )
            turn_state.save()
            return TurnResult(
                entry=entry,
                current_turn=turn_state.current_roommate,
                next_turn=_get_next_in_rotation(turn_state.current_roommate, roommates)
                if turn_state.current_roommate
                else None,
                remaining_bottles=turn_state.remaining_bottles if turn_state.current_roommate else None,
                messages=messages,
            )

        # quantity == 2 by non-current actor: complete current turn and skip actor's next turn.
        action_type = BottleFillEntry.ACTION_FULL_HELP_SKIP
        entry = BottleFillEntry.objects.create(
            roommate=actor,
            target_roommate=current,
            quantity=2,
            action_type=action_type,
        )
        SkipTurn.objects.create(roommate=actor, reason="full_help_skip")
        messages.append(
            f"{actor.name} completed {current.name}'s turn (2 bottles), {actor.name}'s next turn will be skipped."
        )
        next_turn = _next_effective_turn(current, roommates, messages)
        turn_state.current_roommate = next_turn
        turn_state.remaining_bottles = 2 if next_turn else 2
        turn_state.save()
        sent = send_turn_reminder_email(
            next_turn, notify_all=getattr(settings, "TURN_REMINDER_NOTIFY_ALL", False)
        )
        if sent:
            messages.append(f"Reminder email sent to {sent} roommate(s).")
        return TurnResult(
            entry=entry,
            current_turn=turn_state.current_roommate,
            next_turn=_get_next_in_rotation(turn_state.current_roommate, roommates)
            if turn_state.current_roommate
            else None,
            remaining_bottles=turn_state.remaining_bottles if turn_state.current_roommate else None,
            messages=messages,
        )

    if quantity > turn_state.remaining_bottles:
        raise ValidationError(
            f"{current.name} has only {turn_state.remaining_bottles} bottle(s) remaining this turn."
        )

    entry = BottleFillEntry.objects.create(
        roommate=actor,
        target_roommate=current,
        quantity=quantity,
        action_type=action_type,
    )

    turn_state.remaining_bottles -= quantity

    if turn_state.remaining_bottles == 0:
        messages.append(f"{current.name}'s turn completed.")
        next_turn = _next_effective_turn(current, roommates, messages)
        turn_state.current_roommate = next_turn
        turn_state.remaining_bottles = 2 if next_turn else 2
        turn_state.save()
        sent = send_turn_reminder_email(
            next_turn, notify_all=getattr(settings, "TURN_REMINDER_NOTIFY_ALL", False)
        )
        if sent:
            messages.append(f"Reminder email sent to {sent} roommate(s).")
    else:
        messages.append(f"{current.name} has {turn_state.remaining_bottles} bottle remaining.")
        turn_state.save()

    return TurnResult(
        entry=entry,
        current_turn=turn_state.current_roommate,
        next_turn=_get_next_in_rotation(turn_state.current_roommate, roommates)
        if turn_state.current_roommate
        else None,
        remaining_bottles=turn_state.remaining_bottles if turn_state.current_roommate else None,
        messages=messages,
    )


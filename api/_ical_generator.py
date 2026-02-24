from datetime import datetime, timezone

from icalendar import Calendar, Event


def _parse_dt(value):
    """Parse a TeamSnap datetime string into a timezone-aware datetime."""
    if not value:
        return None
    # TeamSnap returns ISO 8601 strings like "2025-03-15T14:00:00Z"
    # or "2025-03-15T14:00:00+00:00"
    s = value.replace("Z", "+00:00")
    return datetime.fromisoformat(s)


def generate_ical(events, locations_by_id, opponents_by_id=None):
    """Generate an iCal VCALENDAR from a list of filtered event dicts.

    Args:
        events: List of TeamSnap event dicts (flat, parsed from Collection+JSON).
        locations_by_id: Dict mapping location_id to location dict.
        opponents_by_id: Dict mapping opponent_id to opponent dict.

    Returns:
        bytes: The iCal data.
    """
    if opponents_by_id is None:
        opponents_by_id = {}
    cal = Calendar()
    cal.add("prodid", "-//ts-subscribe//TeamSnap Filtered Feed//EN")
    cal.add("version", "2.0")
    cal.add("x-wr-calname", "TeamSnap (Attending)")

    for ev in events:
        event_id = ev.get("id")
        start = _parse_dt(ev.get("start_date"))
        if not start:
            continue

        vevent = Event()
        vevent.add("uid", f"teamsnap-event-{event_id}@ts-subscribe")

        is_game = ev.get("is_game")
        name = ev.get("name") or ""
        if is_game and not name:
            opponent_id = ev.get("opponent_id")
            if opponent_id and opponent_id in opponents_by_id:
                name = f"vs {opponents_by_id[opponent_id].get('name', 'TBD')}"
            else:
                name = "Game Day"
        elif not name:
            name = "Untitled"
        prefix = "[Game]" if is_game else "[Event]"
        vevent.add("summary", f"{prefix} {name}")

        vevent.add("dtstart", start)
        end = _parse_dt(ev.get("end_date"))
        if end:
            vevent.add("dtend", end)

        # Location
        location_id = ev.get("location_id")
        if location_id and location_id in locations_by_id:
            loc = locations_by_id[location_id]
            loc_name = loc.get("name", "")
            loc_address = loc.get("address", "")
            if loc_name and loc_address:
                vevent.add("location", f"{loc_name}, {loc_address}")
            elif loc_name:
                vevent.add("location", loc_name)

        # Description
        desc_parts = []
        if ev.get("notes"):
            desc_parts.append(ev["notes"])
        arrive_early = ev.get("minutes_to_arrive_early")
        if arrive_early:
            desc_parts.append(f"Arrive {arrive_early} minutes early")
        if ev.get("is_canceled"):
            desc_parts.append("** CANCELED **")
        if desc_parts:
            vevent.add("description", "\n".join(desc_parts))

        if ev.get("is_canceled"):
            vevent.add("status", "CANCELLED")

        vevent.add("dtstamp", datetime.now(timezone.utc))

        cal.add_component(vevent)

    return cal.to_ical()

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from icalendar import Calendar, Event, Timezone, vText


def _parse_dt(value):
    """Parse a TeamSnap datetime string into a timezone-aware datetime."""
    if not value:
        return None
    s = value.replace("Z", "+00:00")
    return datetime.fromisoformat(s)


def _format_arrival_time(dt, tz):
    """Format a datetime as a human-readable arrival time like TeamSnap does."""
    local = dt.astimezone(tz)
    time_str = local.strftime("%l:%M %p").strip()
    tz_name = tz.key.split("/")[-1].replace("_", " ")
    return f"{time_str} ({tz_name})"


def generate_ical(events, locations_by_id, opponents_by_id=None,
                  team_name="TeamSnap", team_tz_name="UTC"):
    """Generate an iCal VCALENDAR matching TeamSnap's native format.

    Args:
        events: List of TeamSnap event dicts (flat, parsed from Collection+JSON).
        locations_by_id: Dict mapping location_id to location dict.
        opponents_by_id: Dict mapping opponent_id to opponent dict.
        team_name: The team's display name.
        team_tz_name: IANA timezone name for the team (e.g. "Asia/Hong_Kong").

    Returns:
        bytes: The iCal data.
    """
    if opponents_by_id is None:
        opponents_by_id = {}

    tz = ZoneInfo(team_tz_name)

    cal = Calendar()
    cal.add("prodid", "-//ts-subscribe//TeamSnap Filtered Feed//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", f"{team_name} (Attending)")
    cal.add("x-wr-timezone", team_tz_name)

    # Add VTIMEZONE component
    cal.add_component(Timezone.from_ical(
        Timezone(TZID=team_tz_name).to_ical()
    ))

    for ev in events:
        event_id = ev.get("id")
        team_id = ev.get("team_id", "")
        start = _parse_dt(ev.get("start_date"))
        if not start:
            continue

        vevent = Event()
        vevent.add("uid", f"{team_id}-{event_id}")

        # Summary: "Team Name - Event" or "Team Name vs Opponent"
        is_game = ev.get("is_game")
        name = ev.get("name") or ""
        if is_game:
            opponent_id = ev.get("opponent_id")
            if opponent_id and opponent_id in opponents_by_id:
                opponent_name = opponents_by_id[opponent_id].get("name", "")
                if opponent_name:
                    vevent.add("summary", f"{team_name} vs {opponent_name}")
                elif name:
                    vevent.add("summary", f"{team_name} vs {name}")
                else:
                    vevent.add("summary", f"{team_name} - Game Day")
            elif name:
                vevent.add("summary", f"{team_name} vs {name}")
            else:
                vevent.add("summary", f"{team_name} - Game Day")
        else:
            vevent.add("summary", f"{team_name} - {name or 'Event'}")

        # Times in team timezone
        local_start = start.astimezone(tz)
        vevent.add("dtstart", local_start)
        end = _parse_dt(ev.get("end_date"))
        if end:
            local_end = end.astimezone(tz)
            vevent.add("dtend", local_end)

        # Location: address only (like TeamSnap)
        location_id = ev.get("location_id")
        loc_name = ""
        if location_id and location_id in locations_by_id:
            loc = locations_by_id[location_id]
            loc_name = loc.get("name", "")
            loc_address = loc.get("address", "")
            if loc_address:
                vevent.add("location", loc_address)

        # Description: "Location: Venue\n   (Arrival Time: HH:MM AM (TZ))"
        desc_parts = []
        if loc_name:
            arrival_str = _format_arrival_time(start, tz)
            desc_parts.append(f"Location: {loc_name}\n   (Arrival Time: {arrival_str})")
        if ev.get("notes"):
            desc_parts.append(ev["notes"])
        if ev.get("is_canceled"):
            desc_parts.append("** CANCELED **")
        if desc_parts:
            vevent.add("description", " ".join(desc_parts))

        if ev.get("is_canceled"):
            vevent.add("status", "CANCELLED")

        vevent.add("dtstamp", datetime.now(timezone.utc))

        cal.add_component(vevent)

    # The icalendar library double-escapes \n to \\n in DESCRIPTION.
    # TeamSnap uses literal \n (RFC 5545 text newline), so fix it up.
    return cal.to_ical().replace(b"\\\\n", b"\\n")

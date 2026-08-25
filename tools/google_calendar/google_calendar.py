from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from typing import Any

from gcsa.event import Event
from gcsa.google_calendar import GoogleCalendar
from googleapiclient.discovery import build

from google_auth import (
    ToolError,
    as_list,
    get_value,
    google_client_config,
    load_credentials,
    ping as google_ping,
    run_cli,
)


def calendar_id(payload: dict[str, Any] | None = None) -> str:
    if payload:
        value = get_value(payload, "calendarId", "calendar_id")
        if value:
            return str(value)
    return google_client_config().get("email") or "primary"


def calendar_client(payload: dict[str, Any] | None = None) -> GoogleCalendar:
    creds = load_credentials(interactive=False)
    return GoogleCalendar(
        calendar_id(payload),
        credentials=creds,
        save_token=False,
    )


def service_client() -> Any:
    creds = load_credentials(interactive=False)
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def parse_time(value: Any) -> datetime | date | None:
    if value is None or value == "":
        return None
    if isinstance(value, (datetime, date)):
        return value
    text = str(value)
    if len(text) <= 10:
        return date.fromisoformat(text)
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def serialize_event(event: Any) -> dict[str, Any]:
    if isinstance(event, dict):
        start = event.get("start") or {}
        end = event.get("end") or {}
        return {
            "id": event.get("id"),
            "summary": event.get("summary"),
            "description": event.get("description"),
            "location": event.get("location"),
            "start": start.get("dateTime") or start.get("date"),
            "end": end.get("dateTime") or end.get("date"),
            "htmlLink": event.get("htmlLink"),
            "status": event.get("status"),
            "attendees": event.get("attendees"),
            "hangoutLink": event.get("hangoutLink"),
        }
    return {
        "id": getattr(event, "id", None),
        "summary": getattr(event, "summary", None),
        "description": getattr(event, "description", None),
        "location": getattr(event, "location", None),
        "start": str(getattr(event, "start", "") or ""),
        "end": str(getattr(event, "end", "") or ""),
        "htmlLink": getattr(event, "other", {}).get("htmlLink")
        if isinstance(getattr(event, "other", None), dict)
        else None,
        "attendees": [
            getattr(attendee, "email", attendee)
            for attendee in (getattr(event, "attendees", None) or [])
        ],
    }


def ping(_: dict[str, Any]) -> dict[str, Any]:
    result = google_ping()
    result["service"] = "google_calendar"
    if result.get("authorized"):
        calendars = list_calendars({})
        result["calendarCount"] = len(calendars.get("calendars", []))
    return result


def list_calendars(_: dict[str, Any]) -> dict[str, Any]:
    service = service_client()
    items = service.calendarList().list().execute().get("items", [])
    calendars = [
        {
            "id": item.get("id"),
            "summary": item.get("summary"),
            "primary": item.get("primary", False),
            "accessRole": item.get("accessRole"),
            "timeZone": item.get("timeZone"),
        }
        for item in items
    ]
    return {"calendars": calendars}


def list_events(payload: dict[str, Any]) -> dict[str, Any]:
    time_min = parse_time(get_value(payload, "timeMin", "time_min")) or datetime.now(
        timezone.utc
    )
    time_max = parse_time(get_value(payload, "timeMax", "time_max"))
    query = get_value(payload, "query", "q")
    max_results = int(get_value(payload, "maxResults", "max_results", "pageSize", default=50))
    calendar = calendar_client(payload)
    events = list(
        calendar.get_events(
            time_min=time_min,
            time_max=time_max,
            query=query,
            order_by="startTime",
            single_events=True,
        )
    )
    return {"events": [serialize_event(event) for event in events[:max_results]]}


def upcoming(payload: dict[str, Any]) -> dict[str, Any]:
    days = int(get_value(payload, "days", default=14))
    now = datetime.now(timezone.utc)
    time_min = get_value(payload, "timeMin", "time_min") or now.isoformat()
    time_max = get_value(payload, "timeMax", "time_max") or (
        now + timedelta(days=days)
    ).isoformat()
    listed = list_events({**payload, "timeMin": time_min, "timeMax": time_max})
    return {
        "days": days,
        "timeMin": time_min,
        "timeMax": time_max,
        "events": listed.get("events") or [],
    }


def search_events(payload: dict[str, Any]) -> dict[str, Any]:
    return list_events(payload)


def get_event(payload: dict[str, Any]) -> dict[str, Any]:
    event_id = get_value(payload, "eventId", "event_id", "id", required=True)
    calendar = calendar_client(payload)
    event = calendar.get_event(event_id)
    return serialize_event(event)


def _event_from_payload(payload: dict[str, Any], existing: Event | None = None) -> Event:
    summary = get_value(payload, "summary", "title") or (
        getattr(existing, "summary", None) if existing else None
    )
    if not summary:
        raise ToolError("summary is required", "usage")
    start = parse_time(get_value(payload, "startTime", "start_time", "start")) or (
        getattr(existing, "start", None) if existing else None
    )
    end = parse_time(get_value(payload, "endTime", "end_time", "end")) or (
        getattr(existing, "end", None) if existing else None
    )
    if start is None or end is None:
        raise ToolError("startTime and endTime are required", "usage")
    attendees = []
    for item in as_list(get_value(payload, "attendees")):
        if isinstance(item, dict):
            attendees.append(item.get("email") or item.get("emailAddress"))
        else:
            attendees.append(item)
    attendees.extend(as_list(get_value(payload, "attendeeEmails", "attendee_emails")))
    event = Event(
        summary,
        start=start,
        end=end,
        location=get_value(payload, "location")
        or (getattr(existing, "location", None) if existing else None),
        description=get_value(payload, "description")
        or (getattr(existing, "description", None) if existing else None),
        attendees=[value for value in attendees if value],
    )
    if existing is not None and getattr(existing, "id", None):
        event.id = existing.id
    return event


def create_event(payload: dict[str, Any]) -> dict[str, Any]:
    calendar = calendar_client(payload)
    event = calendar.add_event(_event_from_payload(payload))
    return serialize_event(event)


def update_event(payload: dict[str, Any]) -> dict[str, Any]:
    event_id = get_value(payload, "eventId", "event_id", "id", required=True)
    calendar = calendar_client(payload)
    existing = calendar.get_event(event_id)
    updated = _event_from_payload(payload, existing)
    saved = calendar.update_event(updated)
    return serialize_event(saved)


def delete_event(payload: dict[str, Any]) -> dict[str, Any]:
    event_id = get_value(payload, "eventId", "event_id", "id", required=True)
    calendar = calendar_client(payload)
    calendar.delete_event(event_id)
    return {"id": event_id, "deleted": True}


def suggest_time(payload: dict[str, Any]) -> dict[str, Any]:
    duration_minutes = int(
        get_value(payload, "durationMinutes", "duration_minutes", default=60)
    )
    time_min = parse_time(get_value(payload, "timeMin", "time_min")) or datetime.now(
        timezone.utc
    )
    time_max = parse_time(get_value(payload, "timeMax", "time_max")) or (
        time_min + timedelta(days=3)
        if isinstance(time_min, datetime)
        else datetime.now(timezone.utc) + timedelta(days=3)
    )
    calendar_ids = as_list(get_value(payload, "calendarIds", "calendar_ids")) or [
        calendar_id(payload)
    ]
    service = service_client()
    body = {
        "timeMin": (
            time_min if isinstance(time_min, datetime) else datetime.combine(time_min, datetime.min.time(), tzinfo=timezone.utc)
        ).isoformat(),
        "timeMax": (
            time_max if isinstance(time_max, datetime) else datetime.combine(time_max, datetime.min.time(), tzinfo=timezone.utc)
        ).isoformat(),
        "items": [{"id": item} for item in calendar_ids],
    }
    busy = service.freebusy().query(body=body).execute()
    return {
        "durationMinutes": duration_minutes,
        "calendars": busy.get("calendars", {}),
        "timeMin": body["timeMin"],
        "timeMax": body["timeMax"],
    }


def respond_to_event(payload: dict[str, Any]) -> dict[str, Any]:
    event_id = get_value(payload, "eventId", "event_id", "id", required=True)
    response = get_value(payload, "response", "status", required=True)
    mapping = {
        "accepted": "accepted",
        "declined": "declined",
        "tentative": "tentative",
        "needsAction": "needsAction",
    }
    status = mapping.get(str(response), str(response).lower())
    service = service_client()
    cal_id = calendar_id(payload)
    event = service.events().get(calendarId=cal_id, eventId=event_id).execute()
    email = google_client_config().get("email")
    attendees = event.get("attendees") or []
    updated = False
    for attendee in attendees:
        if email and attendee.get("email") == email:
            attendee["responseStatus"] = status
            updated = True
    if not updated:
        attendees.append({"email": email or "primary", "responseStatus": status})
    event["attendees"] = attendees
    saved = service.events().patch(
        calendarId=cal_id,
        eventId=event_id,
        body={"attendees": attendees},
    ).execute()
    return serialize_event(saved)


def commands() -> dict[str, Any]:
    return {
        "ping": ping,
        "list_calendars": list_calendars,
        "upcoming": upcoming,
        "list_events": list_events,
        "search_events": search_events,
        "get_event": get_event,
        "create_event": create_event,
        "update_event": update_event,
        "delete_event": delete_event,
        "suggest_time": suggest_time,
        "respond_to_event": respond_to_event,
    }


def main() -> int:
    os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")
    return run_cli("google_calendar", commands(), example="upcoming --days 14")


if __name__ == "__main__":
    raise SystemExit(main())

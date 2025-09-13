from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from app.db import get_events, get_event_by_id, update_event

ui = FastAPI()

templates = Jinja2Templates(directory="app/templates")


@ui.get("/")
async def index(request: Request):
    """
    Homepage: simple search form.
    """
    return templates.TemplateResponse("index.html", {"request": request})


@ui.get("/results")
async def results(request: Request, from_date: str = None, to_date: str = None):
    """
    Search results page: query events by date range.
    """
    events = get_events(from_date=from_date, to_date=to_date)
    return templates.TemplateResponse(
        "results.html",
        {"request": request, "events": events, "from_date": from_date, "to_date": to_date},
    )


@ui.get("/edit/{event_id}")
async def edit_event(request: Request, event_id: int):
    """
    Edit form for a specific event.
    """
    event = get_event_by_id(event_id)
    if not event:
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("edit.html", {"request": request, "event": event})


@ui.post("/edit/{event_id}")
async def save_event(event_id: int, new_text: str = Form(...)):
    """
    Save updated event text.
    """
    update_event(event_id, new_text)
    return RedirectResponse(f"/edit/{event_id}", status_code=302)

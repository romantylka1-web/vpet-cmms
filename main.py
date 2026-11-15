from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from datetime import datetime, timedelta
import os

# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:////tmp/vpet_cmms.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Asset(Base):
    __tablename__ = "assets"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    asset_type = Column(String)
    location = Column(String)
    criticality = Column(String)
    manufacturer = Column(String)
    model = Column(String)
    serial_number = Column(String)
    install_date = Column(String)
    status = Column(String, default="Operational")
    notes = Column(Text)
    work_orders = relationship("WorkOrder", back_populates="asset")
    pms = relationship("PreventiveMaintenance", back_populates="asset")

class WorkOrder(Base):
    __tablename__ = "work_orders"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(Text)
    asset_id = Column(Integer, ForeignKey("assets.id"))
    priority = Column(String)
    status = Column(String, default="Open")
    type = Column(String)
    assigned_to = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    due_date = Column(String)
    completed_at = Column(DateTime, nullable=True)
    labor_hours = Column(Float, default=0)
    parts_used = Column(Text)
    notes = Column(Text)
    asset = relationship("Asset", back_populates="work_orders")

class PreventiveMaintenance(Base):
    __tablename__ = "preventive_maintenance"
    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"))
    title = Column(String)
    frequency_days = Column(Integer)
    last_performed = Column(String)
    next_due = Column(String)
    checklist = Column(Text)
    active = Column(Boolean, default=True)
    asset = relationship("Asset", back_populates="pms")

class SparePart(Base):
    __tablename__ = "spare_parts"
    id = Column(Integer, primary_key=True, index=True)
    part_number = Column(String, unique=True)
    name = Column(String)
    quantity = Column(Integer, default=0)
    min_quantity = Column(Integer, default=1)
    location = Column(String)
    supplier = Column(String)
    unit_cost = Column(Float)
    notes = Column(Text)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="VPET CMMS")
app.mount("/static", StaticFiles(directory="static"), name="static")
from jinja2 import Environment, FileSystemLoader

templates = Jinja2Templates(directory="templates")
templates.env = Environment(loader=FileSystemLoader("templates"), cache_size=0)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def seed_data():
    db = SessionLocal()
    if db.query(Asset).count() == 0:
        assets = [
            Asset(name="Injection Molder #1", asset_type="Injection Molder", location="Romeoville - Line A", criticality="High", manufacturer="Husky", model="HyPET", serial_number="IM-001", install_date="2018-03-15", status="Operational"),
            Asset(name="Blow Molder #2", asset_type="Blow Molder", location="Romeoville - Line B", criticality="High", manufacturer="Sidel", model="SBO", serial_number="BM-002", install_date="2019-06-20", status="Operational"),
            Asset(name="Chiller System", asset_type="Chiller", location="Romeoville - Utility", criticality="High", manufacturer="Thermal Care", model="TC-500", serial_number="CH-003", install_date="2017-11-10", status="Operational"),
            Asset(name="Conveyor Line A", asset_type="Conveyor", location="Romeoville - Line A", criticality="Medium", manufacturer="Dorner", model="2200", serial_number="CV-004", install_date="2018-03-15", status="Operational"),
            Asset(name="Air Compressor #1", asset_type="Compressor", location="Romeoville - Utility", criticality="High", manufacturer="Atlas Copco", model="GA55", serial_number="AC-005", install_date="2016-09-05", status="Operational"),
        ]
        db.add_all(assets)
        db.commit()
        wos = [
            WorkOrder(title="Hydraulic leak on Injection Molder #1", description="Oil leak near pump assembly", asset_id=1, priority="High", type="Corrective", assigned_to="Tech A", status="Open"),
            WorkOrder(title="Quarterly PM - Blow Molder #2", description="Full preventive maintenance", asset_id=2, priority="Medium", type="Preventive", assigned_to="Tech B", status="Open"),
        ]
        db.add_all(wos)
        pms = [
            PreventiveMaintenance(asset_id=1, title="Monthly Hydraulic Inspection", frequency_days=30, last_performed="2026-10-15", next_due="2026-11-15", checklist="Check oil level, inspect hoses, test pressure"),
            PreventiveMaintenance(asset_id=2, title="Quarterly Full Service", frequency_days=90, last_performed="2026-08-20", next_due="2026-11-20", checklist="Mold inspection, heater bands, air system"),
        ]
        db.add_all(pms)
        parts = [
            SparePart(part_number="HYD-SEAL-01", name="Hydraulic Seal Kit", quantity=5, min_quantity=2, location="Cage A", supplier="Husky Parts", unit_cost=145.00),
            SparePart(part_number="HT-BAND-02", name="Heater Band 220V", quantity=12, min_quantity=4, location="Cage B", supplier="Sidel", unit_cost=85.50),
            SparePart(part_number="FILT-AIR-03", name="Air Filter Element", quantity=8, min_quantity=3, location="Cage A", supplier="Atlas Copco", unit_cost=42.00),
        ]
        db.add_all(parts)
        db.commit()
    db.close()

seed_data()

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    open_wos = db.query(WorkOrder).filter(WorkOrder.status != "Completed").count()
    down_assets = db.query(Asset).filter(Asset.status == "Down").count()
    low_parts = db.query(SparePart).filter(SparePart.quantity <= SparePart.min_quantity).count()
    overdue_pms = db.query(PreventiveMaintenance).filter(PreventiveMaintenance.next_due < datetime.now().strftime("%Y-%m-%d")).count()
    recent_wos = db.query(WorkOrder).order_by(WorkOrder.created_at.desc()).limit(5).all()
    return templates.TemplateResponse(request, "dashboard.html", {
        "request": request,
        "open_wos": open_wos,
        "down_assets": down_assets,
        "low_parts": low_parts,
        "overdue_pms": overdue_pms,
        "recent_wos": recent_wos
    })

@app.get("/assets", response_class=HTMLResponse)
async def assets_list(request: Request, db: Session = Depends(get_db)):
    assets = db.query(Asset).all()
    return templates.TemplateResponse(request, "assets.html", {"request": request, "assets": assets})

@app.get("/assets/new", response_class=HTMLResponse)
async def asset_new(request: Request):
    return templates.TemplateResponse(request, "asset_form.html", {"request": request, "asset": None})

@app.post("/assets/new")
async def asset_create(
    name: str = Form(...),
    asset_type: str = Form(...),
    location: str = Form(...),
    criticality: str = Form(...),
    manufacturer: str = Form(""),
    model: str = Form(""),
    serial_number: str = Form(""),
    db: Session = Depends(get_db)
):
    asset = Asset(name=name, asset_type=asset_type, location=location, criticality=criticality,
                  manufacturer=manufacturer, model=model, serial_number=serial_number)
    db.add(asset)
    db.commit()
    return RedirectResponse("/assets", status_code=303)

@app.get("/workorders", response_class=HTMLResponse)
async def workorders_list(request: Request, db: Session = Depends(get_db)):
    wos = db.query(WorkOrder).order_by(WorkOrder.created_at.desc()).all()
    assets = db.query(Asset).all()
    return templates.TemplateResponse(request, "workorders.html", {"request": request, "workorders": wos, "assets": assets})

@app.get("/workorders/new", response_class=HTMLResponse)
async def wo_new(request: Request, db: Session = Depends(get_db)):
    assets = db.query(Asset).all()
    return templates.TemplateResponse(request, "wo_form.html", {"request": request, "assets": assets, "wo": None})

@app.post("/workorders/new")
async def wo_create(
    title: str = Form(...),
    description: str = Form(""),
    asset_id: int = Form(...),
    priority: str = Form(...),
    type: str = Form(...),
    assigned_to: str = Form(""),
    due_date: str = Form(""),
    db: Session = Depends(get_db)
):
    wo = WorkOrder(title=title, description=description, asset_id=asset_id, priority=priority,
                   type=type, assigned_to=assigned_to, due_date=due_date)
    db.add(wo)
    db.commit()
    return RedirectResponse("/workorders", status_code=303)

@app.post("/workorders/{wo_id}/complete")
async def wo_complete(wo_id: int, db: Session = Depends(get_db)):
    wo = db.query(WorkOrder).filter(WorkOrder.id == wo_id).first()
    if wo:
        wo.status = "Completed"
        wo.completed_at = datetime.utcnow()
        db.commit()
    return RedirectResponse("/workorders", status_code=303)

@app.get("/pm", response_class=HTMLResponse)
async def pm_list(request: Request, db: Session = Depends(get_db)):
    pms = db.query(PreventiveMaintenance).all()
    return templates.TemplateResponse(request, "pm.html", {"request": request, "pms": pms})

@app.get("/parts", response_class=HTMLResponse)
async def parts_list(request: Request, db: Session = Depends(get_db)):
    parts = db.query(SparePart).all()
    return templates.TemplateResponse(request, "parts.html", {"request": request, "parts": parts})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

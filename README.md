# VPET CMMS

Computerized Maintenance Management System prototype for VPET Plastics (Romeoville plant).

## Features
- Dashboard with KPIs
- Asset register (Injection Molders, Blow Molders, Chillers, etc.)
- Work Orders (create, complete, track)
- Preventive Maintenance schedules
- Spare Parts inventory with low-stock highlighting

## Run locally

```bash
cd vpet-cmms
pip install -r requirements.txt
python main.py
```

Then open http://localhost:8000

## Seeded data
Includes sample assets for Romeoville plant (Husky injection, Sidel blow molder, chillers, conveyors, compressors) plus sample work orders and PMs.

## Next steps to production
- Add authentication / roles
- Mobile-responsive improvements + offline
- PM auto-generation of work orders
- Parts consumption on WO completion
- Multi-site support
- PLC/sensor integration for predictive maintenance

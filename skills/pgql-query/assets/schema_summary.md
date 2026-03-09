# Property graph schema summary

## Active property graph
- outage_network

## Vertex labels and properties
- substation: id, name, code, latitude, longitude, capacity_mva, status
- circuit: id, circuit_name, circuit_code, voltage_kv, customers_served, avg_load_mw, peak_load_mw, neighborhood
- asset: id, asset_id, asset_type, condition_score, health_index, status, criticality, latitude, longitude, next_maintenance_due
- customer: id, account_number, name, customer_type, sla_priority, avg_monthly_usage_kwh, latitude, longitude
- outage: id, incident_code, cause_category, weather_condition, customers_affected, duration_minutes, saidi_minutes, safi_count, start_time, end_time
- work_order: id, work_type, priority, status, labor_hours, material_cost, created_time, completed_time
- document: id, document_type, title, tags, source, author, document_date

## Edge labels and relationships
- ORIGINATES_FROM: substation -> circuit
- LOCATED_ON: circuit -> asset
- SERVED_BY: circuit -> customer
- AFFECTED: outage -> circuit
- CAUSED_BY: outage -> asset
- ADDRESSES: work_order -> outage
  - edge properties: id, outage_id, crew_id, work_type, priority, status, labor_hours, material_cost, created_time, completed_time
- SERVICES: work_order -> asset
  - edge properties: id, outage_id, crew_id, work_type, priority, status, labor_hours, material_cost, created_time, completed_time, asset_fk_id
- REFERENCES_OUTAGE: document -> outage
- REFERENCES_ASSET: document -> asset

## Usage notes
- Use the property graph `outage_network`.
- Use the graph labels exactly as defined above.
- Use the listed properties exactly as defined above.
- Oracle property graph queries must keep `MATCH` inside `GRAPH_TABLE(...)` with `COLUMNS(...)`.

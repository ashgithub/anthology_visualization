# Relational schema summary

## Tables
- substations(id, name, code, latitude, longitude, street_address, city, state, zip, capacity_mva, commissioned_on, status, ...)
- circuits(id, circuit_name, circuit_code, substation_id, voltage_kv, length_miles, customers_served, avg_load_mw, peak_load_mw, load_factor_pct, neighborhood, primary_feeder, ...)
- assets(id, asset_id, asset_type, circuit_id, substation_id, latitude, longitude, street_address, installation_date, condition_score, health_index, last_maintenance_date, ...)
- customers(id, account_number, name, customer_type, circuit_id, latitude, longitude, service_address, city, state, zip, contact_phone, ...)
- outages(id, incident_code, circuit_id, root_cause_asset_id, start_time, end_time, cause_category, weather_condition, customers_affected, duration_minutes, saidi_minutes, safi_count, ...)
- work_orders(id, outage_id, asset_id, crew_id, created_time, completed_time, work_type, priority, status, labor_hours, material_cost, notes)
- documents(id, document_type, title, related_outage_id, related_asset_id, related_circuit_id, content, tags, source, author, document_date, embedding)
- crew_assignments(crew_id, outage_id, dispatch_time, arrival_time)
- customer_complaints(id, customer_id, outage_id, category, status, complaint_time, resolution)
- asset_health_history(asset_id, reading_time, condition_score, temperature_c, load_pct)

## Foreign keys
- circuits.substation_id -> substations.id
- assets.circuit_id -> circuits.id
- assets.substation_id -> substations.id
- customers.circuit_id -> circuits.id
- outages.circuit_id -> circuits.id
- outages.root_cause_asset_id -> assets.id
- work_orders.outage_id -> outages.id
- work_orders.asset_id -> assets.id
- documents.related_outage_id -> outages.id
- documents.related_asset_id -> assets.id
- documents.related_circuit_id -> circuits.id
- crew_assignments.outage_id -> outages.id
- customer_complaints.customer_id -> customers.id
- customer_complaints.outage_id -> outages.id
- asset_health_history.asset_id -> assets.id
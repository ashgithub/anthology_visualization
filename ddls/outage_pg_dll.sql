-- Oracle Property Graph definition for outage_network

BEGIN
  EXECUTE IMMEDIATE 'DROP PROPERTY GRAPH outage_network';
EXCEPTION
  WHEN OTHERS THEN NULL;
END;
/

CREATE PROPERTY GRAPH outage_network
  VERTEX TABLES (
    substations KEY (id) LABEL substation
      PROPERTIES (id, name, code, latitude, longitude, capacity_mva, status),
    circuits KEY (id) LABEL circuit
      PROPERTIES (id, circuit_name, circuit_code, voltage_kv, customers_served, avg_load_mw, peak_load_mw, neighborhood),
    assets KEY (id) LABEL asset
      PROPERTIES (id, asset_id, asset_type, condition_score, health_index, status, criticality, latitude, longitude, next_maintenance_due),
    customers KEY (id) LABEL customer
      PROPERTIES (id, account_number, name, customer_type, sla_priority, avg_monthly_usage_kwh, latitude, longitude),
    outages KEY (id) LABEL outage
      PROPERTIES (id, incident_code, cause_category, weather_condition, customers_affected, duration_minutes, saidi_minutes, safi_count, start_time, end_time),
    work_orders KEY (id) LABEL work_order
      PROPERTIES (id, work_type, priority, status, labor_hours, material_cost, created_time, completed_time),
    documents KEY (id) LABEL document
      PROPERTIES (id, document_type, title, tags, source, author, document_date)
  )
  EDGE TABLES (
    circuits AS edge_circuits_origin SOURCE KEY (substation_id) REFERENCES substations (id)
             DESTINATION KEY (id) REFERENCES circuits (id)
             LABEL ORIGINATES_FROM,
    assets AS edge_assets_located SOURCE KEY (circuit_id) REFERENCES circuits (id)
           DESTINATION KEY (id) REFERENCES assets (id)
           LABEL LOCATED_ON,
    customers AS edge_customers_served SOURCE KEY (circuit_id) REFERENCES circuits (id)
              DESTINATION KEY (id) REFERENCES customers (id)
              LABEL SERVED_BY,
    outages AS edge_outages_affected SOURCE KEY (id) REFERENCES outages (id)
            DESTINATION KEY (circuit_id) REFERENCES circuits (id)
            LABEL AFFECTED,
    outages AS edge_outages_caused SOURCE KEY (id) REFERENCES outages (id)
            DESTINATION KEY (root_cause_asset_id) REFERENCES assets (id)
            LABEL CAUSED_BY,
    work_orders AS edge_workorders_addresses SOURCE KEY (id) REFERENCES work_orders (id)
               DESTINATION KEY (outage_id) REFERENCES outages (id)
               LABEL ADDRESSES
               PROPERTIES (
                 id,
                 outage_id,
                 crew_id,
                 work_type,
                 priority,
                 status,
                 labor_hours,
                 material_cost,
                 created_time,
                 completed_time
               ),
    work_orders AS edge_workorders_services SOURCE KEY (id) REFERENCES work_orders (id)
               DESTINATION KEY (asset_id) REFERENCES assets (id)
               LABEL SERVICES
               PROPERTIES (
                 id,
                 outage_id,
                 crew_id,
                 work_type,
                 priority,
                 status,
                 labor_hours,
                 material_cost,
                 created_time,
                 completed_time,
                 asset_id AS asset_fk_id
               ),
    documents AS edge_documents_outage SOURCE KEY (id) REFERENCES documents (id)
              DESTINATION KEY (related_outage_id) REFERENCES outages (id)
              LABEL REFERENCES_OUTAGE,
    documents AS edge_documents_asset SOURCE KEY (id) REFERENCES documents (id)
              DESTINATION KEY (related_asset_id) REFERENCES assets (id)
              LABEL REFERENCES_ASSET
  );
  /
  COMMIT;
  /
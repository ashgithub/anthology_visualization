PROMPT Setting default Select AI profile for ai-playground
begin
  dbms_cloud_ai.set_profile(
        profile_name => 'graph_profile'
    );
end;
/



SELECT AI showsql  What are the most common outage cause categories in the last 6 months
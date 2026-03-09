PROMPT Setting default Select AI profile for ai-playground
begin
  dbms_cloud_ai.set_profile(
        profile_name => 'graph_profile'
    );
end;
/



SELECT AI showsql  What are the most common outage cause categories in the last 6 months
SELECT AI showsql Show me all substations and their capacity in descending order
SELECT AI showsql Find circuits with the highest number of customers served
SELECT AI showsql List assets that are currently in overwatch condition (condition_score < 4)
SELECT AI showsql What are the most common outage cause categories in the last 6 months

SELECT AI showsql  Which work orders are still open and their associated asset types



SELECT AI runsql  What are the most common outage cause categories in the last 6 months
SELECT AI runsql Show me all substations and their capacity in descending order
SELECT AI runsql Find circuits with the highest number of customers served
SELECT AI runsql List assets that are currently in overwatch condition (condition_score < 4)
SELECT AI runsql What are the most common outage cause categories in the last 6 months
SELECT AI runsql  Which work orders are still open and their associated asset types
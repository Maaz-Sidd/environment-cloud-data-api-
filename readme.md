*Overview: 
This report highlights the development of a REST API using lambda, API gateway and dynamodb for habitat monitoring. Lambda functions were created using Python 3.10 for efficient querying and writing to the database through REST API. This report will mention the thought process behind the schema, querying methods and scalability of the solution. 

*Assumptions: 
some assumptions were made for the business requirements:
- old data is required for future analysis of habitat 
- data is not real-time but received every hour or few minutes interval
- each new user means a new habitat which includes sensors for data

*Database schema: 
The data required was time-series so the following were set to be the primary keys: - partition key: habitat_id (s)
																				    - sort key: date (YYYY-MM-DD HH:MM)
 
the rest of the schema consisted of: - temp (for holding temperature data): number
				     				 - humidity: number
				     				 - activity: string
with this setup, the data can be organized with the habitat_id as the partition key and allow multiple entires of the same habitat as long as the date and time is different. Keeping the date as the partition key would cause overriding of data if multiple habitats send data at the same time. 

*API set up: 
used a REST API in api gateway to handle GET and POST requests at the /environment_data endpoint. An API key was also set up for security. Also set up API chaching for the GET requests to take off the load from the requests and save on costs. 

*Lambda functions: 
two lambda functions were created, the first having the trigger be the API to push and retrieve data from dynamodb. Used boto3 querying to efficiently query the data with the given parameters. The second lambda function was triggered by could watch Eventbridge at the first day of every month to create a new table and decrease the WCU and RCU provisioning of the old table. This was done as per the recommendation by AWS for efficiently storing time-series data in dynamodb and saving on costs as the old data wouldn't have write access but allow minimal read access. The following was done with the assumption that the old data wouldn't be accessed as frequently as the new data, this can also be changed to just using 1 table with a date range querying to limit the RCU per request. The following cron was set for the trigger on the first day of every month: cron(0 0 1 * ? *)

*Scalability:
A few different techniques were used to make the solution scalable and cost-efficient.
- Lambda functions: Since they are severless it will automatically scale based on the requirement. querying of the data is done per table basis and using parameters to save on cost on RRU.  
- Dynamic table allocation: one method used to make the application more scalable while saving on costs is by dynamically creating new tables for a new period and decreasing the RRU and WRU of the old one. Reducing the provisioning of the old table is done with the understanding that older data is not as important as newer ones. AWS charges on RRU and WRU so limiting that is the key for scalability and cost savings. If old data is not important to the business then old data can also be removed by setting a TTL and not creating more tables.  
- API gateway caching: another method used to scale the application and save on costs is using caching on the GET API end-point. Assuming the data is not real-time and the delay won't cause issues to the buisness caching can be done up to 6 minutes to limit the number of API calls and save on costs. 

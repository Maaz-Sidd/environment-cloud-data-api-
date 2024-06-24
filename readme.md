*Overview: 
This report is highlighting the development of a REST API using lambda, API gateway and dynamodb for habitat monitoring. Lambda functions were created using python 3.10 for efficient querying and writing to the database through REST API. This report will mention the thought process behind the schema, quering methods and scalability of the solution. 

*Assumptions: 
some assumptions were made for the business requirements:
- old data is required for future analysis of habitat 
- data is not real-time but recieved every hour or few min interval
- each new user means a new habitat which includes sensors for data

*Database scehma: 
The data required was time-series so the following were set to be the primary keys: - partition key: habitat_id (s)
																				    - sort key: date (YYYY-MM-DD HH:MM)
 
the rest of the schema consisted of: - temp (for holding temperature data) : number
				     				 - humidity : number
				     				 - activity : string
with this setup the data can be organized with the habitat_id as the partition key and allow multiple entires of the same habitat as long as the date and time is different. Keeping date as the partition key would cause overriding of data if multiple habitats send data at the same time. 

*API set up: 
used a REST api in api gateway to handle GET and POST requests at the /environment_data endpoint. An API key was also set up for security. Also set up API chaching for the GET requests to take off the load from the requests and save on costs. 

*Lambda functions: 
two lambda functions were created, the first having the trigger be the API to push and retrieve data from dynamodb. Used boto3 quering to efficiently query the data with the given parameters. The second lambda fucntion was triggered by couldwatch eventbridge at the first day of every month to create a new table and decrease the WCU and RCU provisioning of the old table. This was done as per the recomendation by AWS for efficiently storing time-series data in dynamodb and saving on costs as the old data wouldn't have write access but allow minimal read access. The following was done with the assumption that the old data wouldn't be accessed as frequently as the new data, this can also be changed to just using 1 table with date range quering to limit the RCU per request. The following cron was set for the trigger at the first day of every month: cron(0 0 1 * ? *)

*Scalability:
A few different techneques were used to make the solution scalable and cost efficient.
- Lambda functions: Since lambda functions are severless it will automatically scale based on the requirement. quering of the data is done per table basis and using parameters to save on cost on RRU.  
- Dynamic table allocation: one method used to make the applicaiton more scalable while saving on costs is by dynamically creating new tables for a new period and decreasing the RRU and WRU of the old one. Reducing the provisioning of the old table is done with the understanding that older data is not as important as newer one. AWS charges on RRU and WRU so limiting that is the key for scalability and cost savings. If old data is not important to the business then old data can also be removed by setting a TTL and not creating more tables.  
- API gateway caching: another method used to scale the application and save on costs is using caching on the GET API end-point. Assuming the data is not real-time and delay won't cause issues to the buisness caching can be done up to 6 mins to limit the number of API calls and save on costs. 

cost analysis: 
each data input is about 63 bytes, AWS charges for on-demand: - WRU: $1.25/million WRU
															  - RRU: $0.25/million WRU
															  - storage: first 25 GB/ month is free then $0.25 per GB
1 RRU = 4kb
1 WRU = 1kb

pricing information taken from: https://aws.amazon.com/dynamodb/pricing/on-demand/

if each user is writing data every half an hour (48 in a day) and reading around the same then in a month: 
10,000 users: 48 writes/day * 63 bytes/write * 31 days/month * 10,000 users = 0.93744 GB per month 
			  937,440 kb / 4 kb/RRU = 234,360 RRU/month which is less than 1 million RRU so no charge 
			  937,440 kb / 1 kb/WRU = 937,440 WRU/month which is still less than 1 million WRU so no charge
			  0.937 < 25 GB so no charge
			  total = $0
			
100,000 users: 48 writes/day * 63 bytes/write * 31 days/month * 100,000 users = 9.3744 GB per month 
			   9,374,400 kb / 4 kb/RRU = (2,343,600 RRU/month / 1,000,000 RRU) * $1.25 = $2.93/month 
			   9,374,400 kb / 1 kb/WRU = (9,374,400 WRU/month / 1,000,000 WRU) * $0.25 = $2.34/month
 			   9.3744 GB < 25 GB so no charge
			   total = $5.27/month

1,000,000 users: 48 writes/day * 63 bytes/write * 31 days/month * 1,000,000 users = 93.744 GB per month 
			   93,744,000 kb / 4 kb/RRU = (23,436,000 RRU/month / 1,000,000 RRU) * $1.25 = $29.30/month 
			   93,744,000 kb / 1 kb/WRU = (93,744,000 WRU/month / 1,000,000 WRU) * $0.25 = $23.44/month
 			   93.744 GB - 25 GB = 68.744 GB * $0.25 = $17.19/month
			   total = $69.93/month

For older provisioned tables the charge is based on RCU and WCU, which would be 1kb of writes and 4 kb of reads per second. 
taken from: https://aws.amazon.com/dynamodb/pricing/provisioned/

10,000: (48 reads/day * 63 bytes/write * 10,000 users )/ 86400 s/day = 350 bytes/s < 4 kb 
100,000: (48 reads/day * 63 bytes/write * 100,000 users )/ 86400 s/day = 3500 bytes/s < 4 kb
1,000,000: (48 reads/day * 63 bytes/write * 1,000,000 users )/ 86400 s/day = 35000 bytes/s = 35 kb/s / 4 kb/RCU = 8.75 * $0.00013 = $0.0011375

so would need to provision about 10 RCU for older tables 

Lambda function pricing: 
average runtime of 300ms and 128 MB allocated memory.
making the same assumptions as above (48 reads and 48 writes per day per user):
10,000: 96 requests/day * 10,000 users * 31 days/month = 29.76 million request 
100,000: 96 requests/day * 100,000 users * 31 days/month = 297.6 million request 
1,000,000: 96 requests/day * 1,000,000 users * 31 days/month = 2976 million request 

putting these numbers in the AWS pricing calculator (https://calculator.aws/#/createCalculator/Lambda): 
10,000: $17.68 USD /month
100,000: $238.65 USD /month
1,000,000: $2,448.34 USD /month

API gateway pricing: 
taken from: https://aws.amazon.com/api-gateway/pricing/
First 333 million requests	$3.50
Next 667 million requests	$2.80
Next 19 billion requests	$2.38

as seen above with calculations: 
10,000: 29.76 million requests < 333 million
100,000: 297.6 million requests < 333 million 
1,000,000: ((2976 million requests - 333 million) / 667 million ) * $2.80 + $3.50 = $14.60

total for all services estimate:
10,000 users: $17.68 USD /month 
100,000 users: $243.92 USD /month
1,000,000 users: $2,532.87 USD /month 

additional charges can be added with caching data: 

Cache Memory Size (GB)	Price per Hour
0.5 	                $0.02
1.6 	                $0.038
6.1 	                $0.20
13.5	                $0.25
28.4	                $0.50
58.2	                $1.00
118.0	                $1.90
237.0	                $3.80

*future consideration: 
for applications with users over 1 million, a server-full backend can be considered for cost savings. As for database, AWS timestream can be considered for time-series data as it provides native support for such data. Timestream is also optimized for time-series data with built-in functionalities and cost savings. 

*Testing API: 

url: https://aotfrufd7j.execute-api.us-east-1.amazonaws.com/dev/environment_data
requests: GET , POST
possible params for querying: - habitatid = id
							  - date = (YYYY-MM-DD%20H:M)
							  - type = temp or humidity or activity
							  - month = (M-YYYY)
API key: fdlwcFqEe15vkjciPVKRIwB1x16pyNjapS0dIy7h
# Summaryze
Text and YouTube Video Summarizer

## Running
Requirements: 
- docker
- docker-compose

Single instance 
```bash
docker compose up -d --build
```
With load balancing
```bash
docker compose up -d --build --scale api-service=3
```
Shutting down
```bash
docker compose down
```

## Using
The web page will be accessible at http://localhost:80

## Testing
### To check the health of all of the services:
```bash 
docker ps
``` 

### Health endpoints:
```bash
# NGINX API Gateway 
GET http://localhost:80/health 
# DB Service
GET http://localhost:8001/health 
# Transcript Service
GET http://localhost:8002/health 
# LLM Service
GET http://localhost:8003/health 
# Postgres
docker exec -it summaryze-postgres-db-1 pg_isready -U summaryze -d summaries
```

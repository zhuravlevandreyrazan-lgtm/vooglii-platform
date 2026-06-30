# Deploy Next Steps

1. SSH into the server:
   `ssh root@201.51.0.142`
2. Clone the repository:
   `git clone https://github.com/zhuravlevandreyrazan-lgtm/vooglii-platform.git`
3. Enter the project directory:
   `cd vooglii-platform`
4. Create the production env file from the example:
   `cp .env.production.example .env.production`
5. Replace all placeholder values in `.env.production`.
6. Validate the env file before the first boot:
   `python scripts/validate_env.py .env.production`
7. Start the production stack:
   `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`
8. Configure DNS for `vooglii.ru`.
9. Configure Nginx and SSL.
10. Run smoke checks against the deployed endpoints.

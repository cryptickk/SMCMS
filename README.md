# Start backend on local PC
python -m uvicorn app.main:app --reload --port 8000

# Start frontend on local PC
python -m streamlit run .\web\index.py

# Copy local SMCMS folder to aws-folder excluding unnecessary directories and files
robocopy .\SMCMS .\aws-deploy /E `
  /XD .venv venv data .git __pycache__ `
  /XF .env *.csv *.pem

# Send the deployable folder to the EC2 instance from local PC.
scp -i .\municipal_key.pem -r `
  .\aws-deploy ubuntu@<EC2_PUBLIC_IP>:~/SMCMS

# manually create a .env file in EC2 instance and enter credentials in it.
ssh -i .\municipal_key.pem ubuntu@16.170.133.39
nano .env

# Build and Start the containers in the EC2 instance
sudo docker compose up --build -d
sudo docker compose ps --no-trunc

sudo docker ps -a
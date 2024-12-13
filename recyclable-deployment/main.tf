provider "aws" {
  region                  = "us-west-2"
  shared_credentials_files = ["~/.aws/credentials"]
  profile                 = "default"
}

variable "allowed_ips" {
  description = "List of IP addresses allowed for access"
  type        = list(string)
  default     = ["0.0.0.0/0"]  # Add any ip address here for access
}

resource "aws_iam_policy" "ec2_full_access" {
  name        = "ec2_full_access"
  description = "Policy for full access to EC2"
  policy      = jsonencode({
    Version   = "2012-10-17"
    Statement = [{
      Action   = "ec2:*"
      Effect   = "Allow"
      Resource = "*"
    }]
  })
}

resource "aws_iam_role" "ec2_role" {
  name               = "ec2_role"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Principal = { Service = "ec2.amazonaws.com" }
      Effect    = "Allow"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ec2_attach" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = aws_iam_policy.ec2_full_access.arn
}

resource "aws_iam_policy" "rds_full_access" {
  name        = "rds_full_access"
  description = "Policy for full access to RDS"
  policy      = jsonencode({
    Version   = "2012-10-17"
    Statement = [{
      Action   = "rds:*"
      Effect   = "Allow"
      Resource = "*"
    }]
  })
}

resource "aws_iam_role" "rds_role" {
  name               = "rds_role"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Principal = { Service = "rds.amazonaws.com" }
      Effect    = "Allow"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "rds_attach" {
  role       = aws_iam_role.rds_role.name
  policy_arn = aws_iam_policy.rds_full_access.arn
}

resource "aws_db_instance" "django_db" {
  allocated_storage       = 20
  storage_type            = "gp2"
  engine                  = "postgres"
  engine_version          = "16.1"
  instance_class          = "db.t3.micro"
  db_name                 = "recyclable"
  username                = "db_user"
  password                = "f4K20jJb#5"
  delete_automated_backups = true
  skip_final_snapshot     = true
  publicly_accessible     = true
}

resource "aws_security_group" "django_app_sg" {
  name        = "django_app_sg"
  description = "Allow web and SSH traffic"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_ips  # SSH access only from this IP
  }

  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = var.allowed_ips  # Django app access only from this IP
  }

  ingress {
  from_port   = 80
  to_port     = 80
  protocol    = "tcp"
  cidr_blocks = var.allowed_ips
}

ingress {
  from_port   = 443
  to_port     = 443
  protocol    = "tcp"
  cidr_blocks = var.allowed_ips
}

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "rds_sg" {
  name        = "rds_sg"
  description = "Security group for RDS PostgreSQL instance"

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    security_groups = [aws_security_group.django_app_sg.id]  # Allow access from EC2 instance
    cidr_blocks = var.allowed_ips  # Allow direct access only from this IP
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_s3_bucket" "olyns_recyclable" {
  bucket = "olyns-recyclable"

  tags = {
    Name = "Olyns Recyclable Bucket"
  }
}

resource "aws_s3_bucket_ownership_controls" "olyns_recyclable" {
  bucket = aws_s3_bucket.olyns_recyclable.id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}


resource "aws_s3_bucket_policy" "allow_access_from_my_ip" {
  bucket = aws_s3_bucket.olyns_recyclable.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.olyns_recyclable.arn}/*"
        Condition = {
          IpAddress = {
            "aws:SourceIp" = ["99.46.136.61/32", "24.84.244.41/32"]
          }
        }
      }
    ]
  })
}

resource "aws_s3_bucket_website_configuration" "olyns_recyclable" {
  bucket = aws_s3_bucket.olyns_recyclable.id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "error.html"
  }
}

resource "aws_iam_policy" "s3_access" {
  name        = "s3_access_policy"
  description = "Policy for access to S3 bucket"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket",
          "s3:DeleteObject"
        ]
        Effect   = "Allow"
        Resource = [
          aws_s3_bucket.olyns_recyclable.arn,
          "${aws_s3_bucket.olyns_recyclable.arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "s3_attach" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = aws_iam_policy.s3_access.arn
}

resource "random_id" "profile_suffix" {
  byte_length = 8
}

resource "aws_iam_instance_profile" "django_app_profile" {
  name = "django_app_profile-${random_id.profile_suffix.hex}"
  role = aws_iam_role.ec2_role.name
}

variable "django_secret_key" {
  description = "The Django secret key"
  type        = string
  default     = "{KbaoFqdaX+2lflH&CDE)@I@u+7)hi=dibLeH}ufMR<HZ1oDc"
}

resource "aws_instance" "django_app" {
  ami             = "ami-0eb5115914ccc4bc2"
  instance_type   = "t3.micro"
  security_groups = [aws_security_group.django_app_sg.name]
  key_name        = "django_app_keypair"
  iam_instance_profile   = aws_iam_instance_profile.django_app_profile.name

  user_data = <<-EOF
                #!/bin/bash
                set -e
                exec > >(tee /var/log/user_data.log) 2>&1

                echo "............Updating system packages............"
                sudo yum update -y

                echo "............Installing dependencies............"
                sudo yum install -y git python3 python3-pip mesa-libGL gcc openssl-devel bzip2-devel libffi-devel zlib-devel postgresql-devel nginx

                echo "............Set environment variables............"
                sudo tee -a /etc/environment > /dev/null <<EOT
                export DJANGO_SECRET_KEY='${var.django_secret_key}'
                export DB_NAME='${aws_db_instance.django_db.db_name}'
                export DB_USER='${aws_db_instance.django_db.username}'
                export DB_PASSWORD='${aws_db_instance.django_db.password}'
                EOT

                echo "............Load environment variables............"
                eval "$(cat /etc/environment | sed 's/^/export /')"

                echo "............Downloading and installing Python 3.11............"
                cd /opt/
                sudo wget https://www.python.org/ftp/python/3.11.0/Python-3.11.0.tar.xz
                sudo tar xvf Python-3.11.0.tar.xz
                cd Python-3.11.0
                sudo ./configure --enable-optimizations
                sudo make altinstall

                echo "............Downloading Django application............"
                cd /opt/
                sudo git clone https://github.com/Vyngard/recyclable.git
                sudo chown -R $(whoami):$(whoami) /opt/recyclable/
                sudo chmod -R 755 /opt/recyclable
                cd recyclable
                pip3 install virtualenv
                sudo /opt/Python-3.11.0/python -m venv myenv

                echo "............Give permissions and configuring RDS_HOST............"
                RDS_HOST="${aws_db_instance.django_db.endpoint}"
                RDS_HOST=$(echo $RDS_HOST | sed 's/:.*//')
                cp recyclable_proj/settings.py.template recyclable_proj/settings.py
                sed -i "s/{{rds_host}}/$RDS_HOST/" recyclable_proj/settings.py
                VENV_PYTHON="/opt/recyclable/myenv/bin/python"

                echo "............Installing requirements............"
                $VENV_PYTHON -m pip install -r requirements.txt
                $VENV_PYTHON -m pip install gunicorn

                echo "............Configuring Django Environment............"
                export PYTHONPATH=$(pwd)
                export DJANGO_SETTINGS_MODULE='recyclable_proj.settings'
                $VENV_PYTHON manage.py showmigrations
                $VENV_PYTHON manage.py makemigrations recyclable
                $VENV_PYTHON manage.py migrate

                echo "............Creating superuser............"
                echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('tad', 'tad@olyns.com', '8IS4L:F=px0?mM')" | ./myenv/bin/python manage.py shell
                echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('victor', 'victor@olyns.com', '6XI_18L7EPxbwO')" | ./myenv/bin/python manage.py shell

                echo "............Collecting Static Files and set permissions............"
                $VENV_PYTHON manage.py collectstatic --noinput
                sudo chown -R ec2-user:ec2-user /opt/recyclable/recyclable/static
                sudo chmod -R 755 /opt/recyclable/recyclable/static

                echo "............Configuring Gunicorn............"
                sudo tee /etc/systemd/system/gunicorn.service > /dev/null <<EOT
                [Unit]
                Description=gunicorn daemon
                After=network.target

                [Service]
                User=ec2-user
                Group=ec2-user
                WorkingDirectory=/opt/recyclable
                ExecStart=/opt/recyclable/myenv/bin/gunicorn --access-logfile /var/log/gunicorn/access.log --error-logfile /var/log/gunicorn/error.log --workers 3 --bind unix:/run/gunicorn/recyclable.sock recyclable_proj.wsgi:application
                
                # Set environment variables
                Environment="DJANGO_SECRET_KEY=${var.django_secret_key}"
                Environment="DB_NAME=${aws_db_instance.django_db.db_name}"
                Environment="DB_USER=${aws_db_instance.django_db.username}"
                Environment="DB_PASSWORD=${aws_db_instance.django_db.password}"

                [Install]
                WantedBy=multi-user.target
                EOT

                # wait for a moment to ensure all files are created
                sleep 10

                # give permissions
                sudo mkdir -p /opt/recyclable /var/log/gunicorn /run/gunicorn
                sudo touch /var/log/gunicorn/access.log /var/log/gunicorn/error.log
                sudo chown ec2-user:ec2-user /var/log/gunicorn/access.log /var/log/gunicorn/error.log
                sudo chmod 644 /var/log/gunicorn/access.log /var/log/gunicorn/error.log
                sudo chown ec2-user:ec2-user /run/gunicorn
                sudo chmod 755 /run/gunicorn

                # reload systemd and start Gunicorn
                sudo systemctl daemon-reload
                sudo systemctl start gunicorn
                sudo systemctl enable gunicorn

                echo "............Configuring Nginx............"
                sudo tee /etc/nginx/conf.d/recyclable.conf > /dev/null <<EOT
                
                # enable ssl on port 443
                server {
                    listen 443 ssl;
                    server_name recyclable.olyns.com;

                    ssl_certificate /etc/letsencrypt/live/recyclable.olyns.com/fullchain.pem; # managed by Certbot
                    ssl_certificate_key /etc/letsencrypt/live/recyclable.olyns.com/privkey.pem; # managed by Certbot
                    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
                    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot
                    client_max_body_size 10M;

                    location / {
                        # adjust this to use the app port
                        proxy_pass http://unix:/run/gunicorn/recyclable.sock;

                        # standard setup
                        proxy_set_header Host $host;
                        proxy_set_header X-Real-IP $remote_addr;
                        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                        proxy_set_header X-Forwarded-Proto $scheme;
                    }

                    location /static/ {
                        alias /opt/recyclable/recyclable/static/;
                    }

                    location /media/ {
                        alias /opt/recyclable/media/;
                    }

                    error_log /var/log/nginx/error.log;
                    access_log /var/log/nginx/access.log;
                }

                server {
                    if ($host = recyclable.olyns.com) {
                        return 301 https://$host$request_uri;
                    } # managed by Certbot


                    listen 80;
                    server_name recyclable.olyns.com;
                    return 404; # managed by Certbot


                }
                EOT

                sudo nginx -t
                sudo systemctl restart nginx
                sudo systemctl enable nginx

                echo "............Configuration Ended............"
              EOF

  tags = {
    Name = "DjangoAppServer"
  }
}

output "rds_endpoint" {
  value = aws_db_instance.django_db.endpoint
  description = "The endpoint of the RDS instance."
}

output "s3_bucket_website_endpoint" {
  value       = aws_s3_bucket_website_configuration.olyns_recyclable.website_endpoint
  description = "The website endpoint of the S3 bucket for accessing images."
}
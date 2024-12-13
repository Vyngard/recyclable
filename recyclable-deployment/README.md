# Prerequisite
1. Create new credentials in your Amazon account (new access key and secret key), and put it as default credentials in your system.
2. Create a key-pair in EC2 key-pair section with the name `django_app_keypair`. Choose `.ppk` if you have Windows and `RSA` algorithm. Copy the `.ppk` file in project folder.   

3. Go to the Github account -> Settings -> Developer Settings -> Personal Access Tokens -> Fine-grained tokens -> Generate new token. Choose the right owner in `Resource Owner` and repository in `Repository Access`. in `Permissions`, under `Repository Permissions`, select `read-only` for `content`. then click `Generate token`. Copy the token. Now in terraform code, there is a line `https://<token>@github.com/<username>/<repo>`. replace `<token>` with the copied token, `<username>` with your Github username, and `<repo>` with the name of the repository.
4. In terraform code, replace your desire `username`, `email`, and `password` in the following line, to create a superuser in Django app:   

```bash
echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('username', 'email', 'password')" | python3 manage.py shell
```  

5. Right now the allowed ip is `99.46.136.61`. in case you want to change it, in the terraform code, in the `variable "allowed_ips"` add it to the default array.


# Run the Project
1. (if you run the project for the first time) open terminal and type `terraform init` and then hit enter.
2. in the terminal type `terraform apply -auto-approve`
3. wait for the process to finish. It will take some time. when the code is finished you see a message in terminal.
4. even though the process is finished, it will take some time for Django application to be deployed. So, wait for 10 - 15 minutes.
5. in case you want to see the log, you can connect to EC2 using SSH and go to `/var/log/` and see the `user_data.log` file.
5. after the process is finished, in AWS console, find EC2 public ipv4 address, and paste it in the browser `http://<public-ipv4-address>:8000`. (remember the application doesn't have SSL certificate, so it doesn't work on https).
7. if you are using Google Chrome, and you want to capture image, you need to bypass chrome settings as it blocks the camera in http connections.
8. go to `chrome://flags/#unsafely-treat-insecure-origin-as-secure` and in the `Insecure origins treated as secure` section, add the public ipv4 address of the EC2 instance. then click `Enable` and `Relaunch` the browser. now you can capture the image. 
9. REMEMBER to reset this setting after you are done with the project.

# Connect Using SSH (Windows)
1. Download `Putty`. Go to Connection -> SSH -> Auth -> Credentials. Browse the `.ppk` file that you downloaded.
2. In `Putty`, go to Session -> Logging. for username enter `ec2-user@<Public-IPV4-DNS>` and replace `<Public-IPV4-DNS>` with EC2 instance's public DNS. Then click `Open`.
3. If any warning appears, click `Accept`.

# Important
if you want to change anything in `settings.py` file, you need to apply those changes in the `settings.py.template` file, as in the terraform code, `settings.py` file is created from `settings.py.template` file.

# Note
This terraform code creates 2 vpc security-groups, 3 IAM policies, 2 IAM roles, 1 RDS database, 1 EC2, and 1 S3 bucket.

resource "aws_db_instance" "rds_6" {
  identifier           = "rds_6"
  engine               = "postgres"
  instance_class       = "db.t3.micro"
  allocated_storage    = 20
  storage_encrypted    = true
  skip_final_snapshot  = true
  availability_zone    = "ap-southeast-1a"
}

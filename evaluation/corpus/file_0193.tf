resource "aws_s3_bucket" "s3_193" {
  bucket = "s3_193-6085"
}

resource "aws_db_instance" "rds_193" {
  identifier          = "rds_193"
  engine              = "postgres"
  instance_class      = "db.t3.micro"
  allocated_storage   = 20
  publicly_accessible = true
  skip_final_snapshot = true
}

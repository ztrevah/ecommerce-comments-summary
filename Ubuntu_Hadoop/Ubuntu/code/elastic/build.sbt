name := "SparkExample"

version := "0.1"

scalaVersion := "2.12.15"  // Phiên bản Scala bạn �~Qang sử dụng

// Thêm các thư vi�~Gn Spark v�|  Elasticsearch
libraryDependencies ++= Seq(
  "org.apache.spark" %% "spark-core" % "3.4.4",
  "org.apache.spark" %% "spark-sql" % "3.4.4",  // Phiên bản Spark phù hợp
  "org.elasticsearch" %% "elasticsearch-spark-30" % "8.7.0", // Phiên bản Elasticsearch Spark Connector
    // Jackson Databind để xử lý JSON
  "com.fasterxml.jackson.core" % "jackson-databind" % "2.15.2",
  "com.fasterxml.jackson.module" %% "jackson-module-scala" % "2.15.2",

  // Thư viện HTTP (nếu cần thêm tùy chọn, thay cho HttpURLConnection)
  "org.apache.httpcomponents.client5" % "httpclient5" % "5.2.1"
)

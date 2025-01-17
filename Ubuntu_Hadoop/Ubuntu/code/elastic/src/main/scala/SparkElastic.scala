import org.apache.spark.sql.{SparkSession, functions => F}
import org.apache.spark.sql.functions._
import org.apache.spark.sql.types._
import scala.collection.mutable.Queue

import org.apache.spark.sql.{DataFrame}
import java.net.HttpURLConnection
import java.net.URL
import java.io.{BufferedReader, InputStreamReader, OutputStream}
import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.module.scala.DefaultScalaModule

import scala.collection.JavaConverters._

object SparkElastic {

  def main(args: Array[String]): Unit = {
    var count_index = 75;
    // Khởi tạo SparkSession
    val spark = SparkSession.builder()
      .appName("File Processor")
      .master("spark://hadoop-master:7077")
      .getOrCreate()

    import spark.implicits._
    // Đọc danh sách tên file từ file list.csv trên HDFS
    val inputPath = "hdfs://hadoop-master:9000/user/test/data/direction.csv"
    val fileListDF = spark.read
      .option("header", "true") // Giả sử file list.csv có header
      .csv(inputPath)
    
    // Lấy danh sách tên file từ cột "filename" trong file list.csv
    val fileNames = fileListDF.select("filename").as[String].collect()

    // Hàng đợi các file chưa tồn tại
    val pendingFiles = new Queue[String]()
    val pendingFiles2 = Queue("file1", "file2", "file3")

    // Hàm làm sạch và kiểm tra comment
    val cleanAndValidateComment: String => String = comment => {
      val cleaned = comment
        .replaceAll("[^\\p{L}\\p{N}\\s]", " ") // Loại bỏ ký tự đặc biệt
        .replaceAll("\\s+", " ") // Loại bỏ khoảng trắng thừa
        .trim // Xóa khoảng trắng đầu và cuối

      // Kiểm tra nếu có từ nào dài hơn 7 ký tự
      if (cleaned.split("\\s+").exists(_.length >6)) "" else cleaned
    }

    // Định nghĩa UDF
    val cleanAndValidateCommentUDF = F.udf(cleanAndValidateComment)
    
    // Lặp qua từng tên file trong danh sách
    fileNames.foreach { fileName =>
        count_index= count_index +1;
        val fileNameWithCsv = if (!fileName.endsWith(".csv")) s"$fileName.csv" else fileName
        val filePath = s"hdfs://hadoop-master:9000/user/test/data/raw/$fileNameWithCsv"

      // Kiểm tra nếu file tồn tại trên HDFS
      if (hdfsFileExists(filePath)) {
        val df = spark.read.option("header", "true").csv(filePath)

        // Xử lý dữ liệu
        val processedDF = df
          .filter(F.col("comment").isNotNull && F.col("rating_star").isNotNull && F.col("name").isNotNull) // Loại bỏ các dòng chứa null
          .withColumn("rating_star", F.col("rating_star").cast("double")) // Chuyển rating sang kiểu double
          .withColumn("comments", cleanAndValidateCommentUDF(F.col("comment"))) // Làm sạch và kiểm tra comment
          .filter(F.length(F.col("comments")) > 0) // Loại bỏ comment rỗng
          .filter(F.size(F.split(F.col("comments"), " ")) >= 10) // Loại bỏ comment dưới 10 từ
          .filter(F.length(F.col("comments")) <= 3000) // Lọc comment có độ dài <= 3000 ký tự
          .dropDuplicates("comments") // Xóa các comment trùng nhau

        // Tính sao trung bình cho từng sản phẩm
        val averageRatingDF = processedDF.groupBy("name")
          .agg(F.avg("rating_star").as("rating"))

        // Kết hợp sao trung bình với dữ liệu đã xử lý
        val finalDF = processedDF.join(averageRatingDF, Seq("name"), "inner")
          .select("name", "rating", "comments")

        val firstProductName = finalDF.select("name").first().getString(0)
        val filteredDF = finalDF.filter(col("name") === firstProductName)
        val jsonDF = filteredDF
          .withColumn("comment_struct", struct(
            col("comments").as("text"),
            col("rating").cast("int").as("rating")  // Chuyển rating thành số nguyên
          ))
          .groupBy("name")
          .agg(
            collect_list("comment_struct").as("comments")
          )     

        val formattedDF = jsonDF.withColumnRenamed("name", "product_name")
        val jsonData = formattedDF.toJSON.collect().mkString("")
        // print(jsonData)
        val response = getSummaryFromAPI(jsonData)

        // Parse JSON response từ API
        val mapper = new ObjectMapper()
        mapper.registerModule(DefaultScalaModule)

        // Chuyển JSON thành Map
        val jsonResponse = mapper.readValue(response, classOf[Map[String, String]])
        val name = jsonResponse("product_name")
        val summary = jsonResponse("summary")

        val summaryDF = Seq((name, summary)).toDF("name", "summary")
        val enrichedDF = finalDF.join(summaryDF, Seq("name"), "left")

        val esResource = s"comment_index_$count_index"

        // Lưu kết quả vào thư mục clean/ trên HDFS
        // finalDF.write.option("header", "true").csv(s"hdfs://hadoop-master:9000/user/test/data/clean/$fileName")
        val esOptions = Map(
          "es.nodes" -> "192.168.223.43", // URL cluster Elasticsearch
          "es.resource" -> esResource
        )

        enrichedDF.write
          .format("org.elasticsearch.spark.sql")
          .options(esOptions)
          .mode("overwrite")
          .save()
      } else {
        // Nếu file chưa tồn tại, lưu vào hàng đợi để xử lý sau
        pendingFiles.enqueue(fileName)
      }
    }

    // Nếu còn file nào chưa tồn tại thì sẽ quay lại xử lý
    while (pendingFiles.nonEmpty) {
      // println(s"Some files were not found and will be retried: ${pendingFiles.mkString(", ")}")
      // Lặp lại quá trình xử lý cho các file trong hàng đợi
      pendingFiles2.clear()
      pendingFiles.foreach(pendingFiles2.enqueue(_))

      pendingFiles2.foreach { fileName =>
        val fileNameWithCsv2 = if (!fileName.endsWith(".csv")) s"$fileName.csv" else fileName
        val filePath2 = s"hdfs://hadoop-master:9000/user/test/data/raw/$fileNameWithCsv2"

        print(filePath2)
        print("-")
        println(hdfsFileExists(filePath2))
        if (hdfsFileExists(filePath2)) {
          val df2 = spark.read.option("header", "true").csv(filePath2)
          df2.printSchema() // Kiểm tra schema
          df2.show(5)       // Hiển thị 5 dòng đầu tiên để xác nhận dữ liệu
          // Xử lý dữ liệu
          val processedDF2 = df2
            .filter(F.col("comment").isNotNull && F.col("rating_star").isNotNull && F.col("name").isNotNull)
            .withColumn("rating_star", F.col("rating_star").cast("double"))
            .withColumn("cleaned_comment", cleanAndValidateCommentUDF(F.col("comment")))
            .filter(F.length(F.col("cleaned_comment")) > 0)

          // Tính sao trung bình cho từng sản phẩm
          val averageRatingDF2 = processedDF2.groupBy("name")
            .agg(F.avg("rating_star").as("average_rating"))

          // Kết hợp sao trung bình với dữ liệu đã xử lý
          val finalDF2 = processedDF2.join(averageRatingDF2, Seq("name"), "inner")
            .select("name", "average_rating", "cleaned_comment")

          // Lưu kết quả vào thư mục clean/
          finalDF2.write.option("header", "true").csv(s"hdfs://hadoop-master:9000/user/test/data/clean/$fileName")
          pendingFiles.dequeueFirst(_ == fileName)
        }else{
            // Nếu file chưa tồn tại, lưu vào hàng đợi để xử lý sau
            // Trước khi thêm file vào hàng đợi
            if (pendingFiles.contains(fileName)) {
              pendingFiles.dequeueFirst(_ == fileName)
            }
            pendingFiles.enqueue(fileName)
        }
      }
    }
    // Dừng SparkSession
    spark.stop()
  }

  // Hàm kiểm tra sự tồn tại của file trên HDFS
  def hdfsFileExists(filePath: String): Boolean = {
    try {
      val fs = org.apache.hadoop.fs.FileSystem.get(new java.net.URI(filePath), new org.apache.hadoop.conf.Configuration())
      fs.exists(new org.apache.hadoop.fs.Path(filePath))
    } catch {
      case e: Exception => false
    }
  }

  def getSummaryFromAPI(jsonData: String): String = {
    val apiUrl = "https://7040-118-70-128-236.ngrok-free.app/review-product/"
    val url = new URL(apiUrl)
    val connection = url.openConnection().asInstanceOf[HttpURLConnection]
    connection.setRequestMethod("POST")
    connection.setRequestProperty("Content-Type", "application/json")
    connection.setDoOutput(true)

    // Gửi dữ liệu JSON qua POST
    val outputStream = connection.getOutputStream
    outputStream.write(jsonData.getBytes("UTF-8"))
    outputStream.close()

    // Đọc response từ API
    val responseCode = connection.getResponseCode
    if (responseCode == 200) {
      val reader = new BufferedReader(new InputStreamReader(connection.getInputStream))
      val response = reader.lines().toArray.mkString("\n")
      reader.close()
      response
    } else {
      throw new RuntimeException(s"Failed to call API: HTTP $responseCode")
    }
  }

}
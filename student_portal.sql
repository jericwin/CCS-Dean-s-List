-- MariaDB dump 10.19  Distrib 10.4.32-MariaDB, for Win64 (AMD64)
--
-- Host: localhost    Database: student_portal
-- ------------------------------------------------------
-- Server version	10.4.32-MariaDB

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `admin`
--

DROP TABLE IF EXISTS `admin`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `admin` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(255) NOT NULL,
  `password` varchar(255) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `admin`
--

LOCK TABLES `admin` WRITE;
/*!40000 ALTER TABLE `admin` DISABLE KEYS */;
INSERT INTO `admin` VALUES (3,'admin','password','2025-10-07 05:05:24');
/*!40000 ALTER TABLE `admin` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `announcements`
--

DROP TABLE IF EXISTS `announcements`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `announcements` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `title` varchar(255) NOT NULL,
  `body` text NOT NULL,
  `image_path` varchar(255) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `announcements`
--

LOCK TABLES `announcements` WRITE;
/*!40000 ALTER TABLE `announcements` DISABLE KEYS */;
INSERT INTO `announcements` VALUES (1,'hi','sadsadsada',NULL,'2025-10-07 05:10:21');
/*!40000 ALTER TABLE `announcements` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `chat_messages`
--

DROP TABLE IF EXISTS `chat_messages`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `chat_messages` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `sender_role` enum('student','admin') NOT NULL,
  `sender_name` varchar(255) NOT NULL,
  `sender_id` int(11) NOT NULL,
  `receiver_id` int(11) NOT NULL,
  `message` text NOT NULL,
  `timestamp` timestamp NOT NULL DEFAULT current_timestamp(),
  `is_read` tinyint(1) DEFAULT 0,
  PRIMARY KEY (`id`),
  KEY `sender_id` (`sender_id`),
  KEY `receiver_id` (`receiver_id`),
  CONSTRAINT `chat_messages_ibfk_1` FOREIGN KEY (`sender_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `chat_messages_ibfk_2` FOREIGN KEY (`receiver_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `chat_messages`
--

LOCK TABLES `chat_messages` WRITE;
/*!40000 ALTER TABLE `chat_messages` DISABLE KEYS */;
/*!40000 ALTER TABLE `chat_messages` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `deans`
--

DROP TABLE IF EXISTS `deans`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `deans` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `full_name` varchar(255) NOT NULL,
  `email` varchar(255) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `college` varchar(255) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `deans`
--

LOCK TABLES `deans` WRITE;
/*!40000 ALTER TABLE `deans` DISABLE KEYS */;
INSERT INTO `deans` VALUES (3,'Dean User','dean@gmail.com','pbkdf2:sha256:260000$R3VbNfZkqN0eQ9vA$7f94d8b05c8d9c0d5e9e2c4b5f1a3d6e7f8a9b0c1d2e3f4g5h6i7j8k9l0m1n2','College of IT','2025-11-10 09:45:51');
/*!40000 ALTER TABLE `deans` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `deans_list_applications`
--

DROP TABLE IF EXISTS `deans_list_applications`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `deans_list_applications` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `full_name` varchar(255) NOT NULL,
  `course` varchar(255) NOT NULL,
  `cog_filename` varchar(255) DEFAULT NULL,
  `coe_filename` varchar(255) DEFAULT NULL,
  `status` enum('Pending','Approved','Rejected') DEFAULT 'Pending',
  `admin_comment` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `gwa` decimal(5,2) DEFAULT NULL,
  `academic_year` varchar(20) DEFAULT NULL,
  `semester` varchar(10) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `deans_list_applications`
--

LOCK TABLES `deans_list_applications` WRITE;
/*!40000 ALTER TABLE `deans_list_applications` DISABLE KEYS */;
INSERT INTO `deans_list_applications` VALUES (5,'Jeric Punay','bsit_1a','flowchart.jpg','flowchart.jpg','Approved','None','2025-10-28 12:38:06',1.50,'2024-2025','1st'),(7,'Jeric Punay','bsit_4b','AI_VChapter_1.pdf','Blue_and_Light_Orange_Modern_Illustrative_Project_Timeline_Gantt_Chart_2.png','Approved','None','2025-10-28 13:03:04',1.75,NULL,NULL),(8,'Jeric Punay','bsit_1a','Brown_and_White_Modern_Bakery_Menu_Cover_A4_Document_.png','Brown_and_White_Modern_Bakery_Menu_Cover_A4_Document_.png','Approved','None','2025-11-12 15:34:04',1.50,'2025-2026','1st');
/*!40000 ALTER TABLE `deans_list_applications` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `student_feedback`
--

DROP TABLE IF EXISTS `student_feedback`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `student_feedback` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `student_id` int(11) DEFAULT NULL,
  `anonymous` tinyint(1) DEFAULT 1,
  `position` varchar(255) DEFAULT NULL,
  `feedback` text NOT NULL,
  `admin_reply` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `student_id` (`student_id`),
  CONSTRAINT `student_feedback_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `student_feedback`
--

LOCK TABLES `student_feedback` WRITE;
/*!40000 ALTER TABLE `student_feedback` DISABLE KEYS */;
INSERT INTO `student_feedback` VALUES (1,NULL,1,'President','lol',NULL,'2025-10-07 05:09:36'),(2,1,0,'President','sadas',NULL,'2025-10-07 05:10:54');
/*!40000 ALTER TABLE `student_feedback` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `student_notification`
--

DROP TABLE IF EXISTS `student_notification`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `student_notification` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `student_id` int(11) DEFAULT NULL,
  `message` text NOT NULL,
  `status` enum('pending','read','unread') DEFAULT 'pending',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `student_id` (`student_id`),
  CONSTRAINT `student_notification_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=35 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `student_notification`
--

LOCK TABLES `student_notification` WRITE;
/*!40000 ALTER TABLE `student_notification` DISABLE KEYS */;
INSERT INTO `student_notification` VALUES (1,1,'Your application status has been updated to Approved. Comment: None','','2025-10-07 05:13:18'),(2,1,'Your application status has been updated to Pending. Comment: None','pending','2025-10-24 17:41:09'),(3,1,'Your application status has been updated to Pending. Comment: None','pending','2025-10-24 17:50:50'),(4,1,'Your application status has been updated to Pending. Comment: None','pending','2025-10-24 17:58:22'),(5,1,'Your application status has been updated to Pending. Comment: None','pending','2025-10-24 18:39:31'),(6,1,'Your application status has been updated to None. Comment: None',NULL,'2025-10-25 13:13:15'),(7,1,'Your application status has been updated to None. Comment: None',NULL,'2025-10-25 13:15:05'),(8,1,'Your application status has been updated to None. Comment: None',NULL,'2025-10-25 13:16:18'),(9,1,'Your application status has been updated to None. Comment: None',NULL,'2025-10-25 13:16:28'),(10,1,'Your application status has been updated to None. Comment: None',NULL,'2025-10-25 13:22:28'),(11,1,'Your application status has been updated to None. Comment: None',NULL,'2025-10-25 13:25:00'),(12,1,'Your application status has been updated to None. Comment: None',NULL,'2025-10-25 13:25:09'),(13,1,'Your application status has been updated to None. Comment: None',NULL,'2025-10-25 13:28:39'),(14,1,'Your application status has been updated to None. Comment: None',NULL,'2025-10-25 13:32:19'),(15,1,'Your application status has been updated to None. Comment: None',NULL,'2025-10-25 13:32:44'),(16,1,'Your application status has been updated to None. Comment: None',NULL,'2025-10-25 13:37:30'),(17,1,'Your application status has been updated to None. Comment: None',NULL,'2025-10-25 13:41:14'),(18,1,'Your application status has been updated to None. Comment: None',NULL,'2025-10-25 13:41:33'),(19,1,'Your application status has been updated to None. Comment: None',NULL,'2025-10-25 13:41:37'),(20,1,'Your application status has been updated to None. Comment: None',NULL,'2025-10-25 13:41:47'),(21,1,'Your application status has been updated to None. Comment: None',NULL,'2025-10-25 13:41:55'),(22,1,'Your application status has been updated to None. Comment: None',NULL,'2025-10-25 13:41:58'),(23,1,'Your application status has been updated to None. Comment: None',NULL,'2025-10-25 13:41:59'),(24,1,'Your application status has been updated to None. Comment: None',NULL,'2025-10-25 13:44:06'),(25,1,'Your application status has been updated to None. Comment: None',NULL,'2025-10-25 13:45:35'),(26,1,'Your application status has been updated to None. Comment: None',NULL,'2025-10-25 13:46:48'),(27,1,'Your application status has been updated to None. Comment: None',NULL,'2025-10-25 13:47:54'),(28,1,'Your application status has been updated to None. Comment: None',NULL,'2025-10-25 13:47:59'),(29,1,'Your application status has been updated to None. Comment: None',NULL,'2025-10-25 13:48:14'),(30,1,'Your application status has been updated to None. Comment: None',NULL,'2025-10-25 13:48:19'),(31,1,'Your application status has been updated to Approved. Comment: None','','2025-10-28 13:28:40'),(32,1,'Your application status has been updated to Approved. Comment: None','','2025-10-28 13:28:46'),(33,1,'Your application status has been updated to Approved. Comment: None','','2025-11-12 15:49:21'),(34,1,'Your application status has been updated to Approved. Comment: None','','2025-11-12 15:49:26');
/*!40000 ALTER TABLE `student_notification` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `users` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `fullname` varchar(255) NOT NULL,
  `email` varchar(255) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `college` varchar(255) DEFAULT NULL,
  `role` enum('student','admin','dean') DEFAULT 'student',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES (1,'Jeric Punay','punay.jeric@gmail.com','scrypt:32768:8:1$vHXmJdcyUKtc6g46$13310ed8d3314f20a99c830eb737bfcabba5f52e40aa621cbd69791b207b1a9e053da2391d5e218ca38cb05cc3fca03cfe0f0b43cdd14526ce387ed5889ed2e6','College of Computer Studies','student','2025-10-07 04:44:23'),(4,'Dean User','dean@gmail.com','pbkdf2:sha256:260000$abc123$7b3a9e5c...',NULL,'dean','2025-11-10 09:19:52');
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-11-22 13:23:57

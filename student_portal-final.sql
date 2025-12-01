-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Dec 01, 2025 at 07:00 AM
-- Server version: 10.4.32-MariaDB
-- PHP Version: 8.1.25

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `student_portal`
--

-- --------------------------------------------------------

--
-- Table structure for table `admin`
--

CREATE TABLE `admin` (
  `id` int(11) NOT NULL,
  `username` varchar(255) NOT NULL,
  `password` varchar(255) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `admin`
--

INSERT INTO `admin` (`id`, `username`, `password`, `created_at`) VALUES
(3, 'admin', 'password', '2025-10-07 05:05:24');

-- --------------------------------------------------------

--
-- Table structure for table `announcements`
--

CREATE TABLE `announcements` (
  `id` int(11) NOT NULL,
  `title` varchar(255) NOT NULL,
  `body` text NOT NULL,
  `image_path` varchar(255) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `announcements`
--

INSERT INTO `announcements` (`id`, `title`, `body`, `image_path`, `created_at`) VALUES
(1, 'hi', 'sadsadsada', NULL, '2025-10-07 05:10:21');

-- --------------------------------------------------------

--
-- Table structure for table `chat_messages`
--

CREATE TABLE `chat_messages` (
  `id` int(11) NOT NULL,
  `sender_role` enum('student','admin') NOT NULL,
  `sender_name` varchar(255) NOT NULL,
  `sender_id` int(11) NOT NULL,
  `receiver_id` int(11) NOT NULL,
  `message` text NOT NULL,
  `timestamp` timestamp NOT NULL DEFAULT current_timestamp(),
  `is_read` tinyint(1) DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `chat_messages`
--

INSERT INTO `chat_messages` (`id`, `sender_role`, `sender_name`, `sender_id`, `receiver_id`, `message`, `timestamp`, `is_read`) VALUES
(10, 'student', 'None', 5, 0, 'hi', '2025-11-29 08:57:12', 1),
(11, 'admin', 'Admin', 0, 5, 'hello, is there anything I can help you with?', '2025-11-29 08:57:27', 0),
(12, 'student', 'None', 6, 0, 'Hi, I would like to be part of Dean\'s list.', '2025-11-29 09:02:00', 1),
(13, 'admin', 'Admin', 0, 6, 'Sure  please submit your requirements.', '2025-11-29 09:04:58', 0),
(14, 'admin', 'Admin', 0, 6, 'and fuck off!', '2025-11-29 09:08:34', 0);

-- --------------------------------------------------------

--
-- Table structure for table `deans`
--

CREATE TABLE `deans` (
  `id` int(11) NOT NULL,
  `full_name` varchar(255) NOT NULL,
  `email` varchar(255) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `college` varchar(255) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `deans`
--

INSERT INTO `deans` (`id`, `full_name`, `email`, `password_hash`, `college`, `created_at`) VALUES
(3, 'Dean', 'dean@gmail.com', 'scrypt:32768:8:1$l13RcCB8TqkIalD0$1acc7f115a7677cc42662fa17546595a68f025b54b0a182234d8ea019f64cabbcf18a74fbcbcb3aad545014a29b7df82e7246a266c54bd9067307ac13b58f572', 'College of IT', '2025-11-10 09:45:51');

-- --------------------------------------------------------

--
-- Table structure for table `deans_list_applications`
--

CREATE TABLE `deans_list_applications` (
  `id` int(11) NOT NULL,
  `full_name` varchar(255) NOT NULL,
  `course` varchar(255) NOT NULL,
  `cog_filename` varchar(255) DEFAULT NULL,
  `coe_filename` varchar(255) DEFAULT NULL,
  `status` enum('Pending','Approved','Rejected','For Dean Review','Dean Approved','Dean Rejected') DEFAULT 'Pending',
  `admin_comment` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `gwa` decimal(5,2) DEFAULT NULL,
  `academic_year` varchar(20) DEFAULT NULL,
  `semester` varchar(10) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `deans_list_applications`
--

INSERT INTO `deans_list_applications` (`id`, `full_name`, `course`, `cog_filename`, `coe_filename`, `status`, `admin_comment`, `created_at`, `gwa`, `academic_year`, `semester`) VALUES
(5, 'Jeric Punay', 'bsit_1a', 'flowchart.jpg', 'flowchart.jpg', 'For Dean Review', 'None', '2025-10-28 12:38:06', 1.50, '2024-2025', '1st'),
(7, 'Jeric Punay', 'bsit_4b', 'AI_VChapter_1.pdf', 'Blue_and_Light_Orange_Modern_Illustrative_Project_Timeline_Gantt_Chart_2.png', 'Rejected', '', '2025-10-28 13:03:04', 1.75, NULL, NULL),
(8, 'Jeric Punay', 'bsit_1a', 'Brown_and_White_Modern_Bakery_Menu_Cover_A4_Document_.png', 'Brown_and_White_Modern_Bakery_Menu_Cover_A4_Document_.png', 'For Dean Review', 'None', '2025-11-12 15:34:04', 1.50, '2025-2026', '1st');

-- --------------------------------------------------------

--
-- Table structure for table `student_feedback`
--

CREATE TABLE `student_feedback` (
  `id` int(11) NOT NULL,
  `student_id` int(11) DEFAULT NULL,
  `anonymous` tinyint(1) DEFAULT 1,
  `position` varchar(255) DEFAULT NULL,
  `feedback` text NOT NULL,
  `admin_reply` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `student_feedback`
--

INSERT INTO `student_feedback` (`id`, `student_id`, `anonymous`, `position`, `feedback`, `admin_reply`, `created_at`) VALUES
(1, NULL, 1, 'President', 'lol', NULL, '2025-10-07 05:09:36'),
(2, 1, 0, 'President', 'sadas', NULL, '2025-10-07 05:10:54');

-- --------------------------------------------------------

--
-- Table structure for table `student_notification`
--

CREATE TABLE `student_notification` (
  `id` int(11) NOT NULL,
  `student_id` int(11) DEFAULT NULL,
  `message` text NOT NULL,
  `status` enum('pending','read','unread') DEFAULT 'pending',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `student_notification`
--

INSERT INTO `student_notification` (`id`, `student_id`, `message`, `status`, `created_at`) VALUES
(1, 1, 'Your application status has been updated to Approved. Comment: None', '', '2025-10-07 05:13:18'),
(2, 1, 'Your application status has been updated to Pending. Comment: None', 'pending', '2025-10-24 17:41:09'),
(3, 1, 'Your application status has been updated to Pending. Comment: None', 'pending', '2025-10-24 17:50:50'),
(4, 1, 'Your application status has been updated to Pending. Comment: None', 'pending', '2025-10-24 17:58:22'),
(5, 1, 'Your application status has been updated to Pending. Comment: None', 'pending', '2025-10-24 18:39:31'),
(6, 1, 'Your application status has been updated to None. Comment: None', NULL, '2025-10-25 13:13:15'),
(7, 1, 'Your application status has been updated to None. Comment: None', NULL, '2025-10-25 13:15:05'),
(8, 1, 'Your application status has been updated to None. Comment: None', NULL, '2025-10-25 13:16:18'),
(9, 1, 'Your application status has been updated to None. Comment: None', NULL, '2025-10-25 13:16:28'),
(10, 1, 'Your application status has been updated to None. Comment: None', NULL, '2025-10-25 13:22:28'),
(11, 1, 'Your application status has been updated to None. Comment: None', NULL, '2025-10-25 13:25:00'),
(12, 1, 'Your application status has been updated to None. Comment: None', NULL, '2025-10-25 13:25:09'),
(13, 1, 'Your application status has been updated to None. Comment: None', NULL, '2025-10-25 13:28:39'),
(14, 1, 'Your application status has been updated to None. Comment: None', NULL, '2025-10-25 13:32:19'),
(15, 1, 'Your application status has been updated to None. Comment: None', NULL, '2025-10-25 13:32:44'),
(16, 1, 'Your application status has been updated to None. Comment: None', NULL, '2025-10-25 13:37:30'),
(17, 1, 'Your application status has been updated to None. Comment: None', NULL, '2025-10-25 13:41:14'),
(18, 1, 'Your application status has been updated to None. Comment: None', NULL, '2025-10-25 13:41:33'),
(19, 1, 'Your application status has been updated to None. Comment: None', NULL, '2025-10-25 13:41:37'),
(20, 1, 'Your application status has been updated to None. Comment: None', NULL, '2025-10-25 13:41:47'),
(21, 1, 'Your application status has been updated to None. Comment: None', NULL, '2025-10-25 13:41:55'),
(22, 1, 'Your application status has been updated to None. Comment: None', NULL, '2025-10-25 13:41:58'),
(23, 1, 'Your application status has been updated to None. Comment: None', NULL, '2025-10-25 13:41:59'),
(24, 1, 'Your application status has been updated to None. Comment: None', NULL, '2025-10-25 13:44:06'),
(25, 1, 'Your application status has been updated to None. Comment: None', NULL, '2025-10-25 13:45:35'),
(26, 1, 'Your application status has been updated to None. Comment: None', NULL, '2025-10-25 13:46:48'),
(27, 1, 'Your application status has been updated to None. Comment: None', NULL, '2025-10-25 13:47:54'),
(28, 1, 'Your application status has been updated to None. Comment: None', NULL, '2025-10-25 13:47:59'),
(29, 1, 'Your application status has been updated to None. Comment: None', NULL, '2025-10-25 13:48:14'),
(30, 1, 'Your application status has been updated to None. Comment: None', NULL, '2025-10-25 13:48:19'),
(31, 1, 'Your application status has been updated to Approved. Comment: None', '', '2025-10-28 13:28:40'),
(32, 1, 'Your application status has been updated to Approved. Comment: None', '', '2025-10-28 13:28:46'),
(33, 1, 'Your application status has been updated to Approved. Comment: None', '', '2025-11-12 15:49:21'),
(34, 1, 'Your application status has been updated to Approved. Comment: None', '', '2025-11-12 15:49:26'),
(35, 1, 'Your application status has been updated to Rejected. Comment: ', '', '2025-11-27 17:59:37');

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `id` int(11) NOT NULL,
  `fullname` varchar(255) NOT NULL,
  `email` varchar(255) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `college` varchar(255) DEFAULT NULL,
  `role` enum('student','admin','dean') DEFAULT 'student',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`id`, `fullname`, `email`, `password_hash`, `college`, `role`, `created_at`) VALUES
(1, 'Jeric Punay', 'punay.jeric@gmail.com', 'scrypt:32768:8:1$vHXmJdcyUKtc6g46$13310ed8d3314f20a99c830eb737bfcabba5f52e40aa621cbd69791b207b1a9e053da2391d5e218ca38cb05cc3fca03cfe0f0b43cdd14526ce387ed5889ed2e6', 'College of Computer Studies', 'student', '2025-10-07 04:44:23'),
(4, 'Dean User', 'dean@gmail.com', 'pbkdf2:sha256:260000$abc123$7b3a9e5c...', NULL, 'dean', '2025-11-10 09:19:52'),
(5, 'leblanc evaine', 'leblanc@gmail.com', 'scrypt:32768:8:1$JpvP5yyBUI4J2mPa$9a013cd97a955cfaa52fc7f0e7f1005f590a554f67e208274446d74499ab86283bf1cae518e2730a9571e594c6478fc16ab53672c7d8c0c14e0d2765204de8c7', 'College of Computer Studies', 'student', '2025-11-29 08:43:15'),
(6, 'Lux Reyes', 'lux@gmail.com', 'scrypt:32768:8:1$akIW1vJwSVfru37j$249724dadfd993992198c8b040757a770ec645999391eb714af5a9af307a21f42da2d6586cf8774a0dbb9ac7b19f4c96cca3561477d00c6b84a71cb85793c23c', 'College of Computer Studies', 'student', '2025-11-29 09:01:22');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `admin`
--
ALTER TABLE `admin`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `username` (`username`);

--
-- Indexes for table `announcements`
--
ALTER TABLE `announcements`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `chat_messages`
--
ALTER TABLE `chat_messages`
  ADD PRIMARY KEY (`id`),
  ADD KEY `sender_id` (`sender_id`),
  ADD KEY `receiver_id` (`receiver_id`);

--
-- Indexes for table `deans`
--
ALTER TABLE `deans`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `email` (`email`);

--
-- Indexes for table `deans_list_applications`
--
ALTER TABLE `deans_list_applications`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `student_feedback`
--
ALTER TABLE `student_feedback`
  ADD PRIMARY KEY (`id`),
  ADD KEY `student_id` (`student_id`);

--
-- Indexes for table `student_notification`
--
ALTER TABLE `student_notification`
  ADD PRIMARY KEY (`id`),
  ADD KEY `student_id` (`student_id`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `email` (`email`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `admin`
--
ALTER TABLE `admin`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT for table `announcements`
--
ALTER TABLE `announcements`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT for table `chat_messages`
--
ALTER TABLE `chat_messages`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=15;

--
-- AUTO_INCREMENT for table `deans`
--
ALTER TABLE `deans`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT for table `deans_list_applications`
--
ALTER TABLE `deans_list_applications`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=9;

--
-- AUTO_INCREMENT for table `student_feedback`
--
ALTER TABLE `student_feedback`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT for table `student_notification`
--
ALTER TABLE `student_notification`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=36;

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `student_feedback`
--
ALTER TABLE `student_feedback`
  ADD CONSTRAINT `student_feedback_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `users` (`id`) ON DELETE SET NULL;

--
-- Constraints for table `student_notification`
--
ALTER TABLE `student_notification`
  ADD CONSTRAINT `student_notification_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;

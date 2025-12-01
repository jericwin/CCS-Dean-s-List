-- Remove restrictive foreign keys that prevent Admin (who is not in users table) from sending messages
ALTER TABLE chat_messages DROP FOREIGN KEY chat_messages_ibfk_1;
ALTER TABLE chat_messages DROP FOREIGN KEY chat_messages_ibfk_2;
-- Ensure the table supports the chat flow
ALTER TABLE chat_messages
MODIFY sender_id INT NOT NULL;
ALTER TABLE chat_messages
MODIFY receiver_id INT NOT NULL;
# church_backend_mvp
curl -i \
-X POST \
-H "Content-Type: application/json" \
-H "Accept: application/json" \
-H "Authorization: RDJVzHe2Toa6vfglgQg4ug==" \
-d '{"messages": [{ "channel": "whatsapp", "to": "+27762122008", "content": "Test WhatsApp Message Text" }, { "channel": "sms", "to": "+27762122008", "content": "Test SMS Message Text" }]}' \
-s https://platform.clickatell.com/v1/message
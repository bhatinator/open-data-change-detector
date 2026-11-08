from watcher.discord_notifier import send_alert


test_alert = {
    "alert_type": "EVENTS_REVISED",
    "details": {
        "events": [
            {
                "event_id": "test-event-001",
                "changed_fields": [
                    {
                        "field": "properties.mag",
                        "old_value": 2.5,
                        "new_value": 3.1,
                    },
                    {
                        "field": "properties.place",
                        "old_value": "Old location",
                        "new_value": "New location",
                    },
                ],
            }
        ]
    },
}


send_alert(test_alert)

print("Discord test notification sent successfully.")
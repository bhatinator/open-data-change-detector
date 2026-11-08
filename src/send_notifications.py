import time

from watcher.db import get_connection
from watcher.discord_notifier import send_alert


def main():

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    id,
                    payload
                FROM notification_outbox
                WHERE status = 'pending'
                ORDER BY created_at
                FOR UPDATE SKIP LOCKED;
                """
            )

            rows = cur.fetchall()

            print(
                f"Pending notifications: "
                f"{len(rows)}"
            )

            for row_id, payload in rows:

                try:

                    alert = {
                        "alert_type":
                            payload[
                                "alert_type"
                            ],

                        "details":
                            payload[
                                "details"
                            ],
                    }

                    send_alert(alert)

                    cur.execute(
                        """
                        UPDATE notification_outbox
                        SET
                            status = 'sent',
                            sent_at = NOW(),
                            attempts =
                                attempts + 1,
                            last_error = NULL
                        WHERE id = %s;
                        """,
                        (row_id,),
                    )

                    print(
                        f"Sent notification "
                        f"{row_id}"
                    )

                    # Small delay between
                    # separate notifications
                    time.sleep(1)

                except Exception as error:

                    cur.execute(
                        """
                        UPDATE notification_outbox
                        SET
                            status = 'failed',
                            attempts =
                                attempts + 1,
                            last_error = %s
                        WHERE id = %s;
                        """,
                        (
                            str(error),
                            row_id,
                        ),
                    )

                    print(
                        f"Failed notification "
                        f"{row_id}: "
                        f"{error}"
                    )


if __name__ == "__main__":
    main()
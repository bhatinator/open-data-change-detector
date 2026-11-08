import time

from watcher.db import get_connection
from watcher.discord_notifier import send_alert


# Check for new notifications every 5 seconds
POLL_INTERVAL_SECONDS = 5


def process_pending_notifications():
    """
    Find pending notifications and send them to Discord.
    """

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

            if rows:
                print(
                    f"Pending notifications: {len(rows)}"
                )

            for row_id, payload in rows:

                try:

                    alert = {
                        "alert_type":
                            payload["alert_type"],

                        "details":
                            payload["details"],
                    }

                    send_alert(alert)

                    cur.execute(
                        """
                        UPDATE notification_outbox
                        SET
                            status = 'sent',
                            sent_at = NOW(),
                            attempts = attempts + 1,
                            last_error = NULL
                        WHERE id = %s;
                        """,
                        (row_id,),
                    )

                    print(
                        f"Sent notification {row_id}"
                    )

                except Exception as error:

                    cur.execute(
                        """
                        UPDATE notification_outbox
                        SET
                            status = 'failed',
                            attempts = attempts + 1,
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
                        f"{row_id}: {error}"
                    )


def main():

    print("=" * 60)
    print("DISCORD NOTIFICATION WORKER")
    print("=" * 60)

    print(
        f"Checking for notifications every "
        f"{POLL_INTERVAL_SECONDS} seconds."
    )

    print(
        "Press Ctrl+C to stop."
    )

    while True:

        try:

            process_pending_notifications()

        except KeyboardInterrupt:

            print(
                "\nNotification worker stopped."
            )

            break

        except Exception as error:

            print(
                "\nNotification worker error:"
            )

            print(
                f"{type(error).__name__}: {error}"
            )

            print(
                "Will retry on the next cycle."
            )

        try:

            time.sleep(
                POLL_INTERVAL_SECONDS
            )

        except KeyboardInterrupt:

            print(
                "\nNotification worker stopped."
            )

            break


if __name__ == "__main__":
    main()
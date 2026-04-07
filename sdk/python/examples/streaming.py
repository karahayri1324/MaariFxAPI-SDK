import sys
from maarifx import MaarifX

client = MaarifX(api_key="your-api-key-here")

print("Streaming solve...\n")

for event in client.solve_stream(
    image="problem.png",
    text="Solve step by step",
    class_level="9",
    draw_on_image=False,
    detail_level=3,
):
    if event.type == "accepted":
        print(f"[accepted] request_id={event.request_id}")

    elif event.type == "status":
        print(f"[status] {event.message}")

    elif event.type == "thinking":
        pass

    elif event.type == "thinking_done":
        print("[thinking complete]")

    elif event.type == "token":
        sys.stdout.write(event.token or "")
        sys.stdout.flush()

    elif event.type == "complete":
        print(f"\n\n[complete] request_id={event.request_id}")
        if event.view_url:
            print(f"  view_url: {event.view_url}")
        if event.usage:
            print(
                f"  tokens: {event.usage.input_tokens} in"
                f" / {event.usage.output_tokens} out"
            )

    elif event.type == "error":
        print(f"\n[error] {event.message}")

client.close()

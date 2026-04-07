from maarifx import MaarifX

client = MaarifX(api_key="your-api-key-here")

result = client.solve(
    image="problem.png",
    text="Solve this step by step",
    draw_on_image=True,
    detail_level=3,
)

print(f"Request ID : {result.request_id}")
print(f"View URL   : {result.view_url}")
print(f"Tokens used: {result.usage.input_tokens} in / {result.usage.output_tokens} out")

result = client.solve(
    image="problem.png",
    text="What is the answer?",
    draw_on_image=False,
)

print(f"\nText answer:\n{result.text}")

view = client.get_view_url(result.request_id)
print(f"\nView URL: {view.view_url}")

usage = client.get_usage()
print(f"\nToday: {usage.today.requests} requests, ${usage.today.cost_usd:.4f}")

client.close()

from maarifx import MaarifX, MaarifXError

client = MaarifX(api_key="mfx_auth_your-key-here")

user = client.register_user(
    external_id="student-42",
    display_name="Jane Doe",
    email="jane@example.com",
)
print(f"Registered sub-user: {user.sub_user_id}")
print(f"Token: {user.token}")

info = client.verify_user(user.token)
print(f"Token valid: {info.get('valid')}")

result = client.solve(
    image="problem.png",
    text="Solve this problem",
    draw_on_image=True,
    sub_user_token=user.token,
)
print(f"\nSolved! View: {result.view_url}")
print(f"Tokens: {result.usage.input_tokens} in / {result.usage.output_tokens} out")

users = client.list_users()
print(f"\n{len(users)} sub-user(s):")
for u in users:
    print(f"  - {u.external_id} ({u.display_name})")

usage = client.get_usage()
print(f"\nToday: {usage.today.requests} requests, ${usage.today.cost_usd:.4f}")

try:
    client.delete_user("student-42")
    print("\nSub-user student-42 deactivated.")
except MaarifXError as exc:
    print(f"\nCould not deactivate: {exc}")

client.close()

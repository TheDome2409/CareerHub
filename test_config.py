from app.core.config_loader import load_profile, load_scoring

profile = load_profile("config/profile.example.yaml")
scoring = load_scoring("config/scoring.example.yaml")

print(profile.profile.name)
print(profile.profile.salary.target)
print(profile.profile.preferred_roles)

print(scoring.weights)
print(scoring.roles.get("AI Manager"))
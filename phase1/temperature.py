import litellm
import time

def call_n_times(prompt:str, temperature:float, n:int = 2 ) :
    results = []
    for _ in range(n):
        response = litellm.completion(
            model="gemini/gemini-2.5-flash",
            max_tokens=50,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}]
        )
        results.append(response.choices[0].message.content.strip())
        time.sleep(5)
    return results
    
prompt = "Pick a random number between 1 and 10. Output only the number, nothing else."

print("Temperature 0.0 (deterministic):")
for r in call_n_times(prompt,0.0):
    print(f"r: {r}")


print("\nTemperature 1.0 (random):")
for r in call_n_times(prompt,1.5):
    print(f"r: {r}")
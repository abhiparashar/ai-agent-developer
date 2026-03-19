import tiktoken

enc=  tiktoken.get_encoding("cl100k_base")

# Simple example
text = "Hello, My name is abhishek parashar"

tokens = enc.encode(text)

print(tokens)
# Output: [9906, 11, 358, 1097, 264, 8102, 16131, 6975, 15592, 13]

print(f"characters: {len(text)}")
print(f"Tokens: {len(tokens)}")
print(f"Ratio: {len(text)/len(tokens):.1f} chars/token") 

# Code is denser in tokens than prose
code = """
public class HelloWorld {
    public static void main(String[] args) {
        System.out.println("Hello World");
    }
}
"""
code_tokens = enc.encode(code)
print(f"Code chars: {len(code)}, tokens: {len(code_tokens)}")

# See exact breakdown
for token_id in tokens:
    print(f"{token_id:6d} -> '{enc.decode([token_id])}'")

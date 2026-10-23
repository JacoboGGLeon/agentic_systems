from .system import build_system

if __name__ == "__main__":
    result = build_system().run(input("Input: "))
    print(result.text or result.data)


import sys
import importlib

print(f"Python: {sys.version}")

try:
    import optimum.intel
    print(f"optimum-intel version: {optimum.intel.__version__}")
    print(f"optimum-intel file: {optimum.intel.__file__}")
except ImportError:
    print("optimum-intel not installed")

try:
    import optimum
    print(f"optimum version: {optimum.__version__}")
except ImportError:
    print("optimum not installed")
    
print("\nChecking optimum.intel imports:")
try:
    from optimum.intel import OVModelForTextToSpeech
    print("✅ OVModelForTextToSpeech found directly in optimum.intel")
except ImportError as e:
    print(f"❌ Direct import failed: {e}")

try:
    from optimum.intel.openvino import OVModelForTextToSpeech
    print("✅ OVModelForTextToSpeech found in optimum.intel.openvino")
except ImportError as e:
    print(f"❌ Submodule import failed: {e}")

try:
    from optimum.intel.openvino import OVModelForTextToSpeechSeq2Seq
    print("✅ OVModelForTextToSpeechSeq2Seq found")
except ImportError as e:
    print(f"❌ Seq2Seq import failed: {e}")

# sk_kernel.py
# =============
# Semantic Kernel initialization - GOD MODE
# Includes: Windows, FileIO, Time, Memory, Spotify, YouTube, MediaControl, System, Vision, Power, Network

import os
import time
import asyncio
from semantic_kernel import Kernel
from sk_plugins import WindowsPlugin, FileIOPlugin, TimePlugin, PowerPlugin, NetworkPlugin, MemoryPlugin
from sk_plugins_media import SpotifyPlugin, YouTubePlugin, MediaControlPlugin
from sk_plugins_system import SystemPlugin
from sk_plugins_vision import VisionPlugin

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
QWEN_PATH = os.path.join(PROJECT_DIR, "models", "qwen2.5-3b-instruct-ov")


class JarvisKernel:
    """Wrapper for Semantic Kernel with sync execution - GOD MODE."""
    
    def __init__(self):
        self.kernel = None
        self.qwen_pipeline = None
        self._initialize()
    
    def _initialize(self):
        print("[SK] Initializing Semantic Kernel (GOD MODE)...")
        
        self.kernel = Kernel()
        
        print("[SK] Registering core plugins...")
        self.kernel.add_plugin(WindowsPlugin(), plugin_name="windows")
        self.kernel.add_plugin(FileIOPlugin(), plugin_name="fileio")
        self.kernel.add_plugin(TimePlugin(), plugin_name="time")
        self.kernel.add_plugin(MemoryPlugin(), plugin_name="memory")
        
        print("[SK] Registering media plugins...")
        self.kernel.add_plugin(SpotifyPlugin(), plugin_name="spotify")
        self.kernel.add_plugin(YouTubePlugin(), plugin_name="youtube")
        self.kernel.add_plugin(MediaControlPlugin(), plugin_name="mediacontrol")
        
        print("[SK] Registering system plugins...")
        self.kernel.add_plugin(SystemPlugin(), plugin_name="system")
        self.kernel.add_plugin(PowerPlugin(), plugin_name="power")
        self.kernel.add_plugin(NetworkPlugin(), plugin_name="network")
        
        print("[SK] Registering vision plugins...")
        self.kernel.add_plugin(VisionPlugin(), plugin_name="vision")
        
        # Only load Phi-4 if using local model
        try:
            import brain
            # DISABLED: brain.py loads the model for the router.
            # Double loading causes GPU freeze/OOM.
            # if brain.USE_MODEL == "local":
            #     self._load_qwen()
            # else:
            #     print("[SK] Skipping Qwen (using cloud model)")
            print("[SK] Skipping internal model load (Handled by Brain Router)")
        except:
            # self._load_qwen()  # Fallback: load anyway
            print("[SK] Skipping internal model load")
        
        print("[SK] Kernel ready with", len(self.get_all_functions()), "functions")
    
    def _load_qwen(self):
        print("[SK] Loading Qwen 2.5 model...")
        
        if not os.path.exists(QWEN_PATH):
            print("[SK] Warning: Qwen model not found")
            return
        
        try:
            import openvino as ov
            ov_path = os.path.dirname(ov.__file__)
            os.environ["PATH"] = ov_path + ";" + os.path.join(ov_path, "libs") + ";" + os.environ["PATH"]
            
            import openvino_genai as ov_genai
            
            start = time.time()
            for device in ["GPU", "CPU"]:
                try:
                    config = {"CACHE_DIR": "./model_cache"}
                    self.qwen_pipeline = ov_genai.LLMPipeline(QWEN_PATH, device=device, **config)
                    print("[SK] Qwen 2.5 loaded on {} in {:.2f}s".format(device, time.time() - start))
                    return
                except Exception as e:
                    print("[SK] {} failed: {}".format(device, str(e)[:40]))
        except ImportError as e:
            print("[SK] OpenVINO not available:", e)
    
    def get_all_functions(self):
        functions = []
        for plugin_name in self.kernel.plugins:
            plugin = self.kernel.plugins[plugin_name]
            for func_name in plugin.functions:
                functions.append({
                    "plugin": plugin_name,
                    "name": func_name,
                    "function": plugin.functions[func_name]
                })
        return functions
    
    def execute_function(self, plugin_name, function_name, **kwargs):
        """
        Execute a kernel function SYNCHRONOUSLY.
        Handles async SK functions properly.
        """
        try:
            if plugin_name not in self.kernel.plugins:
                return "Unknown plugin: " + plugin_name
            
            plugin = self.kernel.plugins[plugin_name]
            
            if function_name not in plugin.functions:
                return "Unknown function: " + function_name
            
            func = plugin.functions[function_name]
            
            print("[SK] Executing {}.{}".format(plugin_name, function_name))
            
            # Use asyncio to run the async function
            async def run_async():
                result = await func.invoke(self.kernel, **kwargs)
                return result
            
            # Run in event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is already running, create a new one
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, run_async())
                        result = future.result()
                else:
                    result = loop.run_until_complete(run_async())
            except RuntimeError:
                # No event loop, create one
                result = asyncio.run(run_async())
            
            # Extract value
            if hasattr(result, "value"):
                return str(result.value)
            return str(result)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return "Error: " + str(e)
    
    def execute_by_name(self, full_name, **kwargs):
        if "." in full_name:
            plugin_name, func_name = full_name.split(".", 1)
        else:
            for pn in self.kernel.plugins:
                plugin = self.kernel.plugins[pn]
                if full_name in plugin.functions:
                    plugin_name = pn
                    func_name = full_name
                    break
            else:
                return "Function not found: " + full_name
        
        return self.execute_function(plugin_name, func_name, **kwargs)


# Singleton
_kernel_instance = None

def get_kernel():
    global _kernel_instance
    if _kernel_instance is None:
        _kernel_instance = JarvisKernel()
    return _kernel_instance

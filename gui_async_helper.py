"""
Helper para ejecutar código async desde GUI síncrona (Tkinter)

Problema: Tkinter es síncrono, pero la nueva arquitectura usa async/await.
Solución: Este módulo provee utilidades para ejecutar coroutines desde Tkinter.
"""

import asyncio
import threading
from typing import Callable, Any, Optional
from concurrent.futures import Future


class AsyncHelper:
    """
    Helper para ejecutar código async desde Tkinter
    
    Usage:
        # En tu GUI (código síncrono)
        async_helper = AsyncHelper()
        
        async def my_async_function():
            return await some_async_operation()
        
        result = async_helper.run_async(my_async_function())
    """

    def __init__(self):
        """Inicializa el helper"""
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._started = False

    def start_loop(self):
        """
        Inicia el event loop en un thread separado
        
        Debe llamarse UNA VEZ al inicio de la aplicación
        """
        if self._started:
            return

        def run_loop():
            """Ejecuta el event loop"""
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_forever()

        self._thread = threading.Thread(target=run_loop, daemon=True)
        self._thread.start()
        self._started = True

        # Esperar a que el loop esté listo
        while self._loop is None:
            pass

    def run_async(self, coro) -> Any:
        """
        Ejecuta una coroutine de forma síncrona (bloqueante)
        
        Args:
            coro: Coroutine a ejecutar
            
        Returns:
            Resultado de la coroutine
            
        Raises:
            Exception: Si la coroutine falla
        """
        if not self._started:
            self.start_loop()

        # Crear future para obtener el resultado
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)

        # Esperar resultado (bloqueante)
        return future.result()

    def run_async_callback(
            self,
            coro,
            on_success: Optional[Callable[[Any], None]] = None,
            on_error: Optional[Callable[[Exception], None]] = None
    ):
        """
        Ejecuta una coroutine de forma asíncrona (no bloqueante)
        con callbacks
        
        Args:
            coro: Coroutine a ejecutar
            on_success: Callback para éxito (recibe resultado)
            on_error: Callback para error (recibe excepción)
        """
        if not self._started:
            self.start_loop()

        def callback(future: Future):
            """Callback cuando la coroutine termina"""
            try:
                result = future.result()
                if on_success:
                    on_success(result)
            except Exception as e:
                if on_error:
                    on_error(e)

        # Ejecutar coroutine
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        future.add_done_callback(callback)

    def stop_loop(self):
        """Detiene el event loop"""
        if self._loop and self._started:
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._started = False


# Singleton global para facilitar uso
_async_helper = None


def get_async_helper() -> AsyncHelper:
    """
    Obtiene el helper singleton
    
    Returns:
        AsyncHelper global
    """
    global _async_helper
    if _async_helper is None:
        _async_helper = AsyncHelper()
        _async_helper.start_loop()
    return _async_helper


def run_async_from_sync(coro) -> Any:
    """
    Ejecuta una coroutine desde código síncrono (función de conveniencia)
    
    Args:
        coro: Coroutine a ejecutar
        
    Returns:
        Resultado de la coroutine
        
    Example:
        >>> async def fetch_data():
        ...     return await api_client.get("/data")
        >>> 
        >>> # Desde código síncrono (ej: Tkinter)
        >>> result = run_async_from_sync(fetch_data())
    """
    helper = get_async_helper()
    return helper.run_async(coro)


def run_async_with_callback(
        coro,
        on_success: Optional[Callable[[Any], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None
):
    """
    Ejecuta una coroutine con callbacks (función de conveniencia)
    
    Args:
        coro: Coroutine a ejecutar
        on_success: Callback para éxito
        on_error: Callback para error
        
    Example:
        >>> async def fetch_data():
        ...     return await api_client.get("/data")
        >>> 
        >>> def on_success(result):
        ...     print(f"Success: {result}")
        >>> 
        >>> def on_error(error):
        ...     print(f"Error: {error}")
        >>> 
        >>> # Desde código síncrono (no bloquea la GUI)
        >>> run_async_with_callback(fetch_data(), on_success, on_error)
    """
    helper = get_async_helper()
    helper.run_async_callback(coro, on_success, on_error)


# Para compatibilidad con código viejo que usa threading
def run_async_in_thread(async_func, *args, **kwargs):
    """
    Ejecuta una función async en un thread separado
    Compatible con el patrón threading.Thread() del código viejo
    
    Args:
        async_func: Función async a ejecutar
        *args: Argumentos posicionales
        **kwargs: Argumentos nombrados
        
    Example:
        >>> async def my_async_func(param1, param2):
        ...     await asyncio.sleep(1)
        ...     return param1 + param2
        >>> 
        >>> # En lugar de threading.Thread(target=func, daemon=True).start()
        >>> run_async_in_thread(my_async_func, "hello", " world")
    """

    def wrapper():
        coro = async_func(*args, **kwargs)
        run_async_from_sync(coro)

    thread = threading.Thread(target=wrapper, daemon=True)
    thread.start()
    return thread


# ===== EJEMPLO DE USO EN TKINTER =====

if __name__ == "__main__":
    import tkinter as tk
    from tkinter import ttk


    # Simulación de función async (como las del API Integration Context)
    async def fetch_api_data(delay: float = 1.0):
        """Simula una llamada async a la API"""
        await asyncio.sleep(delay)
        return {"status": "success", "data": "Hello from async!"}


    async def fetch_with_error():
        """Simula un error en la API"""
        await asyncio.sleep(0.5)
        raise ValueError("Simulated API error")


    # GUI de ejemplo
    class ExampleGUI:
        def __init__(self, root):
            self.root = root
            self.root.title("Async Helper - Demo")
            self.root.geometry("500x400")

            # Inicializar async helper
            self.async_helper = get_async_helper()

            # UI
            ttk.Label(root, text="Demo: Ejecutar código async desde Tkinter",
                      font=("Arial", 12, "bold")).pack(pady=10)

            # Método 1: Bloqueante (espera resultado)
            ttk.Button(
                root,
                text="Método 1: Llamada Bloqueante (freezea GUI)",
                command=self.blocking_call
            ).pack(pady=5, fill=tk.X, padx=20)

            # Método 2: No bloqueante con callbacks
            ttk.Button(
                root,
                text="Método 2: Llamada No Bloqueante (recomendado)",
                command=self.non_blocking_call
            ).pack(pady=5, fill=tk.X, padx=20)

            # Método 3: Con thread
            ttk.Button(
                root,
                text="Método 3: En Thread Separado",
                command=self.threaded_call
            ).pack(pady=5, fill=tk.X, padx=20)

            # Método 4: Manejo de errores
            ttk.Button(
                root,
                text="Método 4: Manejo de Errores",
                command=self.error_handling_call
            ).pack(pady=5, fill=tk.X, padx=20)

            # Log area
            ttk.Label(root, text="Log:", font=("Arial", 10, "bold")).pack(pady=(20, 5))
            self.log_text = tk.Text(root, height=10, width=60)
            self.log_text.pack(pady=5, padx=20)

        def log(self, message: str):
            """Agrega mensaje al log"""
            self.log_text.insert(tk.END, f"{message}\n")
            self.log_text.see(tk.END)

        def blocking_call(self):
            """Método 1: Llamada bloqueante (NO RECOMENDADO en GUI)"""
            self.log("🔄 Iniciando llamada bloqueante...")
            self.log("⚠️  La GUI se congelará...")

            # ❌ ESTO BLOQUEA LA GUI
            result = run_async_from_sync(fetch_api_data(2.0))

            self.log(f"✅ Resultado: {result}")

        def non_blocking_call(self):
            """Método 2: Llamada no bloqueante con callbacks (RECOMENDADO)"""
            self.log("🔄 Iniciando llamada no bloqueante...")
            self.log("✅ La GUI sigue responsive!")

            def on_success(result):
                self.log(f"✅ Éxito: {result}")

            def on_error(error):
                self.log(f"❌ Error: {error}")

            # ✅ ESTO NO BLOQUEA LA GUI
            run_async_with_callback(
                fetch_api_data(2.0),
                on_success=on_success,
                on_error=on_error
            )

        def threaded_call(self):
            """Método 3: En thread separado (COMPATIBLE CON CÓDIGO VIEJO)"""
            self.log("🔄 Iniciando en thread separado...")

            async def async_operation():
                result = await fetch_api_data(1.5)
                # Nota: Para actualizar GUI, necesitas usar root.after()
                self.root.after(0, lambda: self.log(f"✅ Resultado en thread: {result}"))

            # ✅ Compatible con threading.Thread del código viejo
            run_async_in_thread(async_operation)

        def error_handling_call(self):
            """Método 4: Manejo de errores"""
            self.log("🔄 Probando manejo de errores...")

            def on_success(result):
                self.log(f"✅ Éxito: {result}")

            def on_error(error):
                self.log(f"❌ Error capturado: {error}")

            run_async_with_callback(
                fetch_with_error(),
                on_success=on_success,
                on_error=on_error
            )


    # Ejecutar
    root = tk.Tk()
    app = ExampleGUI(root)
    root.mainloop()

    # Limpiar
    get_async_helper().stop_loop()

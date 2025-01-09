
Set up a virtual environment (Preferred)
```bash
uv venv
```
Once you’ve created a virtual environment, you may activate it.

On Windows, run:
```bash
.venv\Scripts\activate
```
On Unix or MacOS, run:
```bash
source .venv/bin/activate
```
To deactivate :
```bash
deactivate
```
> More information about virtual environments can be found [here](https://docs.python.org/3/tutorial/venv.html)

## Install dependencies
```bash
uv sync
```



```bash
playwright install --with-deps chromium
```

## Update configuration

   - If you used AZD to deploy the resources just run the code below
   ```bash
   azd env get-values > .env
   ```` 
   - Alternatively, copy `.env.sample` (under src) into `.env`

> Important: Magentic-One code uses code execution, you need to have Docker installed to run the examples if you use local execution

## Run
```bash
python m13.py
```
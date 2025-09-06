readme file

how to Run the project
1. python main.py example.py # example.py is the input file , 5 default iterations
2. python main.py sample.py --max-iterations 3 --force-stop # force stop after 3 iteration

# Smart interactive mode (recommended)
python main.py code.py --mode=full_scan --fix-mode=smart

# Automatic optimization
python main.py code.py --mode=full_scan --fix-mode=automatic

# Custom thresholds
python main.py code.py --score-threshold=90 --max-iterations=10
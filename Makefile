all: clean desktop

desktop: clean
	python3 desktop_binds.py

clean:
	rm -rf binds/*

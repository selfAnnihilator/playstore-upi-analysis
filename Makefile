.PHONY: all scrape clean themes analyse dashboard sample

all: clean themes analyse

scrape:
	uv run python src/scrape.py

clean:
	uv run python src/clean.py

themes:
	uv run python src/themes.py

sample:
	uv run python src/themes.py --sample

analyse:
	uv run jupyter nbconvert --to notebook --execute --inplace notebooks/analysis.ipynb

dashboard:
	uv run streamlit run dashboard/app.py

index.html : README.md static/skeleton.css static/box.svg static/template.html
	pandoc -s README.md -o index.html -c static/skeleton.css --template static/template.html -T mkrepo

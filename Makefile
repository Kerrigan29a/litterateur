VERSION = $(shell python3 setup.py --version)

all: build

clean:
	-rm litterateur/main_0.py
	-rm litterateur/main_1.py
	-rm litterateur/main_2.py

distclean: clean
	-rm -r litterateur
	-rm -r *.egg-info
	-rm -r build
	-rm -r *.md.json

release: distclean build
	git tag -a v$(VERSION) -m "Release version $(VERSION)"
	git push origin HEAD
	git push origin tag v$(VERSION)

test: litterateur/main_1.py litterateur/main_2.py
	@if cmp -s litterateur/main_1.py litterateur/main_2.py; then \
		echo TEST OK; \
	else \
		echo TEST ERROR; \
		diff -a -u litterateur/main_1.py litterateur/main_2.py; \
		false; \
	fi

build: test
	mv litterateur/main_1.py litterateur/__init__.py
	sed 's/litterateur\/main_.\.py .*$$/..\/bootstrap\.py ..\/README\.md/' litterateur/script.py > litterateur/__main__.py
	rm litterateur/script.py
	rm litterateur/main_2.py litterateur/main_0.py
	printf "# WARNING: DO NOT EDIT ANY FILE IN THIS FOLDER\n" > litterateur/README.md
	head -n 5 litterateur/__init__.py | tail -n 2 | sed -e 's/^# //; s/; DO NOT EDIT./  /'  -e 's/\(\.\.\/.*\) \(\.\.\/.*\)/\[\1\]\(\1\) \[\2\]\(\2\)/'>> litterateur/README.md

litterateur/main_2.py: litterateur/main_1.py README.md
	python3 $^ main.py:$@ script.py:litterateur/script.py -o -D
	sed 's/litterateur\/main_.\.py .*$$/..\/bootstrap\.py ..\/README\.md/' $@ > $(@:.py=.tmp.py)
	rm $@
	mv $(@:.py=.tmp.py) $@

litterateur/main_1.py: litterateur/main_0.py README.md
	python3 $^ main.py:$@ script.py:litterateur/script.py -o -D
	sed 's/litterateur\/main_.\.py .*$$/..\/bootstrap\.py ..\/README\.md/' $@ > $(@:.py=.tmp.py)
	rm $@
	mv $(@:.py=.tmp.py) $@

litterateur/main_0.py: README.md bootstrap.py
	-mkdir litterateur
	python3 bootstrap.py $< $@

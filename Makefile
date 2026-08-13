.PHONY: validate validate-local validate-links stage package clean

STAGING_DIR ?= ../senior-infra-ops-analyst-nori-staging
PACKAGE_ZIP ?= ../senior-infra-ops-analyst-skillset-v$(shell python3 -c 'import json; print(json.load(open("nori.json"))["version"])').zip

validate: validate-local

validate-local:
	bash tests/validate-package.sh

validate-links:
	bash tests/validate-links.sh

stage: validate-local
	python3 scripts/build_nori_staging.py --source . --destination "$(STAGING_DIR)" --replace

package: stage
	cd "$(STAGING_DIR)" && zip -r "$(abspath $(PACKAGE_ZIP))" .

clean:
	rm -rf ../senior-infra-ops-analyst-skillset-v*.zip .tmp .tmp-* validation-output build dist coverage .cache

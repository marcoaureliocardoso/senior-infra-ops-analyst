.PHONY: validate validate-local validate-links package

validate: validate-local

validate-local:
	bash tests/validate-package.sh

validate-links:
	bash tests/validate-links.sh

package: validate-local
	cd .. && zip -r senior-infra-ops-analyst-skillset-v$(shell python3 -c 'import json; print(json.load(open("senior-infra-ops-analyst/nori.json"))["version"])').zip senior-infra-ops-analyst

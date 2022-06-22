REPO_HUB = iconloop
NAME = icon2-node
VERSION = v1.2.10
NTP_VERSION = ntp-4.2.8p15
IS_LOCAL = true
BASE_IMAGE = goloop-icon
IS_NTP_BUILD = false
GOLOOP_PATH = goloop
DEBUG = false

ifeq ($(DEBUG), true)
	VERBOSE_OPTION = -v
else
	VERBOSE_OPTION =
endif

ifeq ($(debug), true)
	VERBOSE_OPTION = -v
	DEBUG = true
else
	VERBOSE_OPTION =
endif
GOLOOP_BUILD_CMD = "goloop-icon-image"

ifdef version
VERSION = $(version)
endif

ifdef service
SERVICE = $(service)
endif

ifdef VERSION_ARG
VERSION = $(VERSION_ARG)
endif
ifdef REPO_HUB_ARG
REPO_HUB = $(REPO_HUB_ARG)
endif

TAGNAME = $(VERSION)
VCS_REF = $(strip $(shell git rev-parse --short HEAD))
BUILD_DATE = $(strip $(shell date -u +"%Y-%m-%dT%H:%M:%S%Z"))
GIT_DIRTY  = $(shell cd ${GOLOOP_PATH}; git diff --shortstat 2> /dev/null | tail -n1 )

ifeq ($(IS_LOCAL), true)
DOCKER_BUILD_OPTION = --progress=plain --no-cache --rm=true
else
DOCKER_BUILD_OPTION = --no-cache --rm=true
endif

ifeq ($(MAKECMDGOALS) , bash)
	DOWNLOAD_URL:="https://networkinfo.solidwallet.io/info"
	DOWNLOAD_URL_TYPE:="indexing"
#	SEEDS:="20.20.6.86:7100"
#	AUTO_SEEDS:=True
	SERVICE:=MainNet
#	CC_DEBUG:="true"
	IS_AUTOGEN_CERT:=true
    PRIVATE_KEY_FILENAME:="YOUR_KEYSTORE_FILENAME.der"
    NGINX_THROTTLE_BY_IP_VAR:="\$$binary_remote_addr"
	LOCAL_TEST:="true"
#	FASTEST_START:="true"
#	MIGRATION_START="true"
#	MIG_DB="true"
	NTP_REFRESH_TIME:="30"
	MAIN_TIME_OUT:="30"
	ROLE:=0
	GOLOOP_CONSOLE_LEVEL:="trace"
	GOLOOP_LOG_LEVEL:="trace"
	LOG_OUTPUT_TYPE:="console"
#	GOLOOP_NODE_SOCK:="/goloop/cli.sock"
#	GOLOOP_EE_SOCKET:="/goloop/ee.sock"

endif

define colorecho
      @tput setaf 6
      @echo $1
      @tput sgr0
endef

UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Linux)
    ECHO_OPTION = "-e"
    SED_OPTION =
endif
ifeq ($(UNAME_S),Darwin)
    ECHO_OPTION = ""
	SED_OPTION = ''
endif

ifeq ($(USE_COLOR), false)
	NO_COLOR=
	OK_COLOR=
	ERROR_COLOR=
	WARN_COLOR=
else
	NO_COLOR=\033[0m
	OK_COLOR=\033[32m
	ERROR_COLOR=\033[31m
	WARN_COLOR=\033[93m
endif

TEST_FILES := $(shell find tests -name '*.yml')

.PHONY: all build push test tag_latest release ssh bash

all: build_goloop_base build
hub: push_hub tag_latest
version:
	@echo $(VERSION)

print_version:
	@echo $(ECHO_OPTION) "$(OK_COLOR) VERSION-> $(VERSION)  REPO-> $(REPO_HUB)/$(NAME):$(TAGNAME) $(NO_COLOR) IS_LOCAL: $(IS_LOCAL)"
#	@$(shell echo $(ECHO_OPTION) "$(OK_COLOR) ----- Build Environment ----- \n $(NO_COLOR)")

make_debug_mode:
	@$(shell echo $(ECHO_OPTION) "$(OK_COLOR) ----- DEBUG Environment ----- $(MAKECMDGOALS)  \n $(NO_COLOR)" >&2)\
		$(shell echo "" > DEBUG_ARGS) \
			$(foreach V, \
				$(sort $(.VARIABLES)), \
				$(if  \
					$(filter-out environment% default automatic, $(origin $V) ), \
						$($V=$($V)) \
					$(if $(filter-out "SHELL" "%_COLOR" "%_STRING" "MAKE%" "colorecho" ".DEFAULT_GOAL" "CURDIR" "TEST_FILES" "DOCKER_BUILD_OPTION" , "$V" ),  \
						$(shell echo $(ECHO_OPTION) '$(OK_COLOR)  $V = $(WARN_COLOR) $($V) $(NO_COLOR) ' >&2;) \
						$(shell echo '-e $V=$($V)  ' >> DEBUG_ARGS)\
					)\
				)\
			)

make_build_args:
	@$(shell echo $(ECHO_OPTION) "$(OK_COLOR) ----- Build Environment ----- \n $(NO_COLOR)" >&2)\
	   $(shell echo "" > BUILD_ARGS) \
		$(foreach V, \
			 $(sort $(.VARIABLES)), \
			 $(if  \
				 $(filter-out environment% default automatic, $(origin $V) ), \
				 	 $($V=$($V)) \
				 $(if $(filter-out "SHELL" "%_COLOR" "%_STRING" "MAKE%" "colorecho" ".DEFAULT_GOAL" "CURDIR" "TEST_FILES" "DOCKER_BUILD_OPTION" "GIT_DIRTY", "$V" ),  \
					$(shell echo $(ECHO_OPTION) '$(OK_COLOR)  $V = $(WARN_COLOR) $($V) $(NO_COLOR) ' >&2;) \
				 	$(shell echo "--build-arg $V=$($V)  " >> BUILD_ARGS)\
				  )\
			  )\
		 )

test:   make_build_args print_version
	python3 ./tests/test_*.py $(VERBOSE_OPTION)

changeconfig: make_build_args
		@CONTAINER_ID=$(shell docker run -d $(REPO_HUB)/$(NAME):$(TAGNAME)) ;\
		 echo "COPY TO [$$CONTAINER_ID]" ;\
		 docker cp "src/." "$$CONTAINER_ID":/src/ ;\
		 docker exec -it "$$CONTAINER_ID" sh -c "echo `date +%Y-%m-%d:%H:%M:%S` > /.made_day" ;\
		 echo "COMMIT [$$CONTAINER_ID]" ;\
		 docker commit -m "Change the configure files `date`" "$$CONTAINER_ID" $(REPO_HUB)/$(NAME):$(TAGNAME) ;\
		 echo "STOP [$$CONTAINER_ID]" ;\
		 docker stop "$$CONTAINER_ID" ;\
		 echo "CLEAN UP [$$CONTAINER_ID]" ;\
		 docker rm "$$CONTAINER_ID"


change_version:
		@#$(call chdir, $(GOLOOP_PATH))
		@#cd $(GOLOOP_PATH) && git checkout $(VERSION);

		$(call colorecho, "-- Change Goloop Version ${VERSION} --")
		@git submodule update --init --recursive --remote;
		@cd $(GOLOOP_PATH) && git fetch origin --tags && git checkout $(VERSION);

		@if [ '${GIT_DIRTY}' != '' ]  ; then \
				echo '[CHANGED] ${GIT_DIRTY}'; \
				git pull ;\
		fi


check-and-reinit-submodules:
		@if git submodule status | egrep -q '^[-]|^[+]' ; then \
				echo "INFO: Need to reinitialize git submodules"; \
				git submodule update --init; \
		fi


build_goloop_base: make_build_args change_version
		$(call colorecho, "-- Build goloop base image --")
		cd $(GOLOOP_PATH) && $(MAKE) $(GOLOOP_BUILD_CMD)


build: make_build_args
		docker build $(DOCKER_BUILD_OPTION) -f Dockerfile \
			$(shell cat BUILD_ARGS) \
			-t $(REPO_HUB)/$(NAME):$(TAGNAME) .
		docker rmi -f goloop-icon
		$(call colorecho, "\n\nSuccessfully build '$(REPO_HUB)/$(NAME):$(TAGNAME)'")
		@echo "==========================================================================="
		@docker images | grep  $(REPO_HUB)/$(NAME) | grep $(TAGNAME)


show_labels: make_build_args
		docker $(REPO_HUB)/$(NAME):$(TAGNAME) | jq .[].Config.Labels

build_ci: make_build_args change_version
		cd $(GOLOOP_PATH) && $(MAKE) goloop-icon-image
		docker build $(shell cat BUILD_ARGS) -f Dockerfile \
		-t $(REPO_HUB)/$(NAME):$(TAGNAME) .
		docker rmi -f goloop-icon

clean:
		docker images | egrep '^goloop/(.*)-deps' | awk '{print $$3}' | xargs -n 1 docker rmi -f


push: print_version
		#docker tag  $(NAME):$(VERSION) $(REPO_HUB)/$(NAME):$(TAGNAME)
		docker push $(REPO_HUB)/$(NAME):$(TAGNAME)


prod: print_version
		docker tag $(REPO_HUB)/$(NAME):$(TAGNAME)  $(REPO_HUB)/$(NAME):$(VERSION)
		docker push $(REPO_HUB)/$(NAME):$(VERSION)


push_hub: print_version
		#docker tag  $(NAME):$(VERSION) $(REPO_HUB)/$(NAME):$(VERSION)
		docker push $(REPO_HUB)/$(NAME):$(TAGNAME)


tag_latest: print_version
		docker tag  $(REPO_HUB)/$(NAME):$(TAGNAME) $(REPO_HUB)/$(NAME):latest
		docker push $(REPO_HUB)/$(NAME):latest


bash: make_debug_mode print_version
	docker run  $(shell cat DEBUG_ARGS) -p 9000:9000 -p 7100:7100 -it -v $(PWD)/config:/goloop/config -v ${PWD}/s6:/s6-int \
		-v $(PWD)/logs:/goloop/logs -v $(PWD)/ctx:/ctx -v $(PWD)/data:/goloop/data -e VERSION=$(TAGNAME) -v $(PWD)/src:/src --entrypoint /bin/bash \
		--name $(NAME) --cap-add SYS_TIME --rm $(REPO_HUB)/$(NAME):$(TAGNAME)


f_bash: make_debug_mode print_version
		docker run  $(shell cat DEBUG_ARGS) -p 9000:9000 -p 7100:7100 -it -v $(PWD)/config:/goloop/config \
		-v $(PWD)/logs:/goloop/logs -v $(PWD)/ctx:/ctx -v $(PWD)/data:/goloop/data -e VERSION=$(TAGNAME) -v $(PWD)/src:/src --entrypoint /bin/bash \
		--name $(NAME) --network host --restart on-failure $(REPO_HUB)/$(NAME):$(TAGNAME)


list:
		@echo "$(OK_COLOR) Tag List - $(REPO_HUB)/$(NAME) $(NO_COLOR)"
		@curl -s  https://registry.hub.docker.com/v2/repositories/$(REPO_HUB)/$(NAME)/tags | jq --arg REPO "$(REPO_HUB)/$(NAME):" -r '.=("\($$REPO)"+.results[].name)'
		$(call colorecho, "-- END --")


change_docker:
	sed -i $(SED_OPTION) "s/$(REPO_HUB)\/$(NAME).*/$(REPO_HUB)\/$(NAME):$(VERSION)/g" docker-compose.yml


gendocs: change_docker
	@$(shell ./makeMarkDown.sh)

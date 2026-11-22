function showMode(mode) {
    document.querySelectorAll('.tabs button').forEach(function(button) {
        button.classList.toggle('active', button.dataset.mode === mode);
    });
    document.querySelectorAll('form.toolform').forEach(function(form) {
        form.hidden = form.dataset.mode !== mode;
    });
}
document.querySelectorAll('.tabs button').forEach(function(button) {
    button.addEventListener('click', function() {
        showMode(button.dataset.mode);
        //The address shows the tab and its form, ready to search, replacing the address rather than adding to the history
        var form = document.querySelector('form.toolform[data-mode="' + button.dataset.mode + '"]');
        var params = new URLSearchParams(new FormData(form));
        params.set('run', '0');
        history.replaceState(null, '', '/?' + params);
    });
});
showMode(document.querySelector('aside').dataset.mode);

function showOptions(form) {
    var tool = form.elements.tool.value;
    form.querySelectorAll('fieldset[data-tool]').forEach(function(fieldset) {
        fieldset.style.display = fieldset.dataset.tool === tool ? '' : 'none';
    });
}

var searchRunning = false;

function setSearching(searching) {
    searchRunning = searching;
    document.querySelectorAll('button[type="submit"]').forEach(function(button) {
        button.disabled = searching;
    });
}

//Going home while a search is running stops the search first
document.querySelector('header h1 a').addEventListener('click', function(event) {
    if (searchRunning) {
        event.preventDefault();
        fetch('/stop?job=' + currentJob).then(function() {
            location.href = '/';
        });
    }
});

var stages = {waiting: 'Waiting for another search', starting: 'Starting', search: 'Searching OpenAlex',
              institutions: 'Looking up institutions',
              authors: 'Expanding co-authors', works: "Fetching co-authors' works", checking: 'Checking careers',
              full_works: 'Fetching full author lists', references: 'Fetching references',
              co_cited: 'Fetching co-cited papers', citing: 'Fetching citing works',
              funders: 'Looking up funders'};

//Scripts inserted with innerHTML do not run, so replace each with a new script element
function runScripts(element) {
    element.querySelectorAll('script').forEach(function(old) {
        var script = document.createElement('script');
        script.text = old.text;
        old.replaceWith(script);
    });
}

//Clicking a column heading sorts the table by that column; clicking it again reverses the order
function makeSortable(element) {
    element.querySelectorAll('table').forEach(function(table) {
        var headings = table.querySelectorAll('th');
        headings.forEach(function(heading, column) {
            heading.addEventListener('click', function() {
                var body = table.tBodies[0];
                var rows = Array.from(body.rows);
                var ascending = heading.dataset.sorted !== 'ascending';
                var numeric = rows.every(function(row) {
                    var text = row.cells[column].textContent.trim();
                    return text === '' || !isNaN(Number(text));
                });
                rows.sort(function(first, second) {
                    var a = first.cells[column].textContent.trim();
                    var b = second.cells[column].textContent.trim();
                    var order;
                    if (numeric) {
                        order = Number(a) - Number(b);
                    } else {
                        order = a.localeCompare(b, undefined, {sensitivity: 'base'});
                    }
                    return ascending ? order : -order;
                });
                rows.forEach(function(row) { body.appendChild(row); });
                headings.forEach(function(other) { delete other.dataset.sorted; });
                heading.dataset.sorted = ascending ? 'ascending' : 'descending';
            });
        });
    });
}

//Follow this window's own search; a stopped or replaced search is no longer followed
function poll(jobId) {
    fetch('/status?job=' + jobId).then(function(response) { return response.json(); }).then(function(job) {
        if (jobId !== currentJob) {
            return;
        }
        if (job.running) {
            var bar = document.getElementById('bar');
            var finished = job.total !== null && job.done >= job.total;
            document.getElementById('stage').textContent = finished ? 'Producing result' : stages[job.stage];
            if (job.total === null || finished) {
                bar.removeAttribute('value');
                document.getElementById('count').textContent = '';
            } else {
                bar.max = job.total;
                bar.value = job.done;
                document.getElementById('count').textContent = job.done + ' of ' + job.total;
            }
            setTimeout(function() { poll(jobId); }, 500);
            return;
        }
        fetch('/result?job=' + jobId).then(function(response) { return response.text(); }).then(function(result) {
            var results = document.getElementById('results');
            results.innerHTML = result;
            runScripts(results);
            makeSortable(results);
            document.getElementById('progress').hidden = true;
            setSearching(false);
        }).catch(lostServer);
    }).catch(lostServer);
}

//If the server stops answering, say so rather than waiting for ever
function lostServer() {
    document.getElementById('progress').hidden = true;
    var message = document.createElement('div');
    message.className = 'error';
    message.textContent = 'Lost contact with the dashboard server. Check that it is still running, then reload the page.';
    var results = document.getElementById('results');
    results.innerHTML = '';
    results.appendChild(message);
    setSearching(false);
}

//Stopping ends the search on the server but leaves the form as it was, ready to search again
var currentJob = null;

document.getElementById('stop').addEventListener('click', function() {
    var jobId = currentJob;
    currentJob = null;
    fetch('/stop?job=' + jobId).then(function() {
        document.getElementById('progress').hidden = true;
        var message = document.createElement('div');
        message.textContent = 'Search stopped.';
        var results = document.getElementById('results');
        results.innerHTML = '';
        results.appendChild(message);
        setSearching(false);
    }).catch(lostServer);
});

function startSearch(params) {
    currentJob = null;
    document.getElementById('results').innerHTML = '';
    setSearching(true);
    document.getElementById('progress').hidden = false;
    document.getElementById('bar').removeAttribute('value');
    document.getElementById('stage').textContent = stages.starting;
    document.getElementById('count').textContent = '';
    fetch('/search?' + params).then(function(response) { return response.json(); }).then(function(reply) {
        currentJob = reply.job;
        poll(reply.job);
    }).catch(lostServer);
}

document.querySelectorAll('form.toolform').forEach(function(form) {
    form.elements.tool.addEventListener('change', function() { showOptions(form); });
    showOptions(form);
    form.addEventListener('submit', function(event) {
        event.preventDefault();
        var params = new URLSearchParams(new FormData(form));
        history.pushState(null, '', '/?' + params);
        startSearch(params);
    });
});

//The server fills the form in from the URL, so going back or forward reloads the page
window.addEventListener('popstate', function() {
    location.reload();
});

//Offer matches for the text typed so far in a find box; choosing one fills in the identifier field
function setupFinder(boxId, choicesId, url, fieldName) {
    var box = document.getElementById(boxId);
    var choices = document.getElementById(choicesId);
    var field = document.querySelector('input[name="' + fieldName + '"]');
    var timer = null;

    function find(text) {
        if (text.length < 3) {
            choices.hidden = true;
            return;
        }
        fetch(url + encodeURIComponent(text)).then(function(response) { return response.json(); }).then(function(reply) {
            choices.innerHTML = '';
            if (reply.error) {
                showChoiceMessage(reply.error);
                return;
            }
            var candidates = reply.candidates;
            candidates.forEach(function(candidate) {
                var choice = document.createElement('div');
                choice.className = 'choice';
                var title = document.createElement('strong');
                title.textContent = candidate.name;
                var details = document.createElement('span');
                details.textContent = candidate.details;
                choice.appendChild(title);
                choice.appendChild(details);
                choice.addEventListener('click', function() {
                    field.value = candidate.value;
                    box.value = candidate.name;
                    choices.hidden = true;
                    field.dispatchEvent(new Event('change'));
                });
                choices.appendChild(choice);
            });
            choices.hidden = candidates.length === 0;
        }).catch(function() {
            choices.innerHTML = '';
            showChoiceMessage('Lost contact with the dashboard server.');
        });
    }

    function showChoiceMessage(text) {
        var message = document.createElement('div');
        message.className = 'choice failed';
        message.textContent = text;
        choices.appendChild(message);
        choices.hidden = false;
    }

    box.addEventListener('input', function() {
        clearTimeout(timer);
        timer = setTimeout(function() { find(box.value); }, 300);
    });

    //Typing an identifier by hand means the find box no longer describes it
    field.addEventListener('input', function() {
        box.value = '';
        choices.hidden = true;
    });
}

setupFinder('author_name', 'author_choices', '/authors?name=', 'author');
setupFinder('work_title', 'work_choices', '/works?title=', 'doi');
setupFinder('institution_name', 'institution_choices', '/institutions?name=', 'institution');

//Each topic level's dropdown offers the entries within the choice above it; domain and field must be chosen
var levels = ['domain', 'field', 'subfield', 'topic'];

function levelSelect(position) {
    return document.querySelector('select[data-level="' + levels[position] + '"]');
}

function emptyLevel(position) {
    var select = levelSelect(position);
    var first = document.createElement('option');
    first.value = '';
    first.textContent = position < 2 ? 'Choose' : 'Any';
    select.innerHTML = '';
    select.appendChild(first);
    return first;
}

function fillLevel(position) {
    var first = emptyLevel(position);
    for (var later = position + 1; later < levels.length; later++) {
        emptyLevel(later);
    }
    var parent = position === 0 ? '' : levelSelect(position - 1).value;
    if (position > 0 && !parent) {
        return;
    }
    var params = new URLSearchParams({level: levels[position], parent: parent});
    fetch('/children?' + params).then(function(response) { return response.json(); }).then(function(reply) {
        if (reply.error) {
            first.textContent = reply.error;
            return;
        }
        var select = levelSelect(position);
        reply.candidates.forEach(function(child) {
            var option = document.createElement('option');
            option.value = child.value;
            option.textContent = child.name;
            select.appendChild(option);
        });
        //An address from an earlier search restores its choices, once, level by level
        if (select.dataset.value) {
            select.value = select.dataset.value;
            select.dataset.value = '';
            if (select.value && position + 1 < levels.length) {
                fillLevel(position + 1);
            }
        }
    }).catch(function() {
        first.textContent = 'Lost contact with the dashboard server.';
    });
}

levels.forEach(function(level, position) {
    if (position + 1 < levels.length) {
        levelSelect(position).addEventListener('change', function() { fillLevel(position + 1); });
    }
});
fillLevel(0);

//Fill the suggestions of topic boxes from the works of the author chosen, whenever the author or dates change
var authorForm = document.querySelector('form.toolform[data-mode="author"]');
var topicTimer = null;

function suggestTopics() {
    var inputs = authorForm.querySelectorAll('input[data-suggest="author_topics"]');
    var author = authorForm.elements.author.value;
    if (inputs.length === 0 || !author) {
        return;
    }
    var params = new URLSearchParams({author: author, from_date: authorForm.elements.from_date.value,
                                      to_date: authorForm.elements.to_date.value});
    fetch('/topics?' + params).then(function(response) { return response.json(); }).then(function(reply) {
        inputs.forEach(function(input) {
            var list = document.getElementById(input.getAttribute('list'));
            list.innerHTML = '';
            reply.candidates.forEach(function(name) {
                var option = document.createElement('option');
                option.value = name;
                list.appendChild(option);
            });
        });
    }).catch(function() {
        //Suggestions are only a convenience; without them the box still takes any text
    });
}

function suggestTopicsSoon() {
    clearTimeout(topicTimer);
    topicTimer = setTimeout(suggestTopics, 500);
}

authorForm.elements.author.addEventListener('input', suggestTopicsSoon);
authorForm.elements.author.addEventListener('change', suggestTopicsSoon);
authorForm.elements.from_date.addEventListener('change', suggestTopicsSoon);
authorForm.elements.to_date.addEventListener('change', suggestTopicsSoon);
suggestTopics();

var initialFields = {search: 'search_term', paper: 'doi', author: 'author', institution: 'institution'};
var initial = new URLSearchParams(location.search);
//An address with run=0 only fills in the form, leaving the search to be started by hand
if (initial.get(initialFields[initial.get('mode') || 'search']) && initial.get('run') !== '0') {
    startSearch(initial);
}

<%inherit file="../layouts/main.mako"/>
<%!
    import datetime

    import sickrage
    from sickrage.core.common import SKIPPED, WANTED, UNAIRED, ARCHIVED, IGNORED, SNATCHED, SNATCHED_PROPER, SNATCHED_BEST, FAILED
    from sickrage.core.common import Quality, qualityPresets, statusStrings, qualityPresetStrings, cpu_presets
%>
<%block name="content">
<div id="content800">

<h1 class="header">${header}</h1>
<div id="summary2" class="align-left">
<h3>Backlog Search:</h3>
<a class="btn" href="/manage/manageSearches/forceBacklog"><i class="icon-exclamation-sign"></i> Force</a>
<a class="btn" href="/manage/manageSearches/pauseBacklog?paused=${('1', '0')[bool(backlogPaused)]}"><i class="icon-${('paused', 'play')[bool(backlogPaused)]}"></i> ${('Pause', 'Unpause')[bool(backlogPaused)]}</a>
% if not backlogRunning:
    Not in progress<br>
% else:
    ${('', 'Paused:')[bool(backlogPaused)]}
    Currently running<br>
% endif
<br>

<h3>Daily Search:</h3>
<a class="btn" href="/manage/manageSearches/forceSearch"><i class="icon-exclamation-sign"></i> Force</a>
${('Not in progress', 'In Progress')[dailySearchStatus]}<br>
<br>

<h3>Find Propers Search:</h3>
    <a class="btn ${('disabled', '')[bool(sickrage.srConfig.DOWNLOAD_PROPERS)]}"
       href="/manage/manageSearches/forceFindPropers"><i class="icon-exclamation-sign"></i> Force</a>
    % if not sickrage.srConfig.DOWNLOAD_PROPERS:
    Propers search disabled <br>
% elif not findPropersStatus:
    Not in progress<br>
% else:
    In Progress<br>
% endif
<br>

<h3>Search Queue:</h3>
Backlog: <i>${queueLength['backlog']} pending items</i></br>
Daily: <i>${queueLength['daily']} pending items</i></br>
Manual: <i>${queueLength['manual']} pending items</i></br>
Failed: <i>${queueLength['failed']} pending items</i></br>
</div>
</div>
</%block>

from pathlib import Path
from unittest.mock import patch

from matchplay_score import export, web


def test_static_export_preserves_scores_links_and_history(tmp_path):
    tournament = {
        'arenas': [{'arenaId': 1, 'name': 'Stars'}],
        'players': [{'playerId': 1, 'name': 'Test Player'}],
    }
    cards = [{'playerId': 1, 'singlePlayerGames': [
        {'arenaId': 1, 'playerId': 1, 'score': 1234}]}]
    with patch.object(export, 'get_tournament_data_cached', return_value=tournament), \
         patch.object(export, 'get_cards', return_value=cards), \
         patch('matchplay_score.ranking.get_tournament_data_cached', return_value=tournament), \
         patch('matchplay_score.ranking.get_cards', return_value=cards), \
         patch.object(web, 'get_tournament_data_cached', return_value=tournament):
        pages = export.export_site(tmp_path, '/scorehigh')
    assert len(pages) == 5
    ranking = (tmp_path / 'ranking/281672/index.html').read_text(encoding='utf-8')
    assert '617,000' in ranking
    assert '/scorehigh/static/portal.css' in ranking
    assert '/scorehigh/player/281672/Test%20Player' in ranking
    assert 'data-static-snapshot="true"' in ranking
    assert (tmp_path / 'player/281672/Test Player/index.html').is_file()
    assert (tmp_path / '404.html').is_file()
    assert (tmp_path / 'static/windows.css').is_file()
    assert (tmp_path / 'static/fonts/DSEG14Classic-Bold.woff2').is_file()
    assert (tmp_path / 'static/fonts/DSEG-LICENSE.txt').is_file()
    assert (tmp_path / 'static/images/score-high-for-trans-lives.jpg').is_file()
    how = (tmp_path / 'how-it-works/281672/index.html').read_text(encoding='utf-8')
    assert '531,800,000' in how
    assert '/scorehigh/how-it-works/281672' in ranking
    assert not web.app.config.get('SNAPSHOT_AT')


def test_export_rejects_relative_base_path(tmp_path):
    import pytest
    with pytest.raises(ValueError, match='relative'):
        export.export_site(tmp_path, '/../bad')

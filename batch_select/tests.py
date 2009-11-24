from django.conf import settings

if getattr(settings, 'TESTING_BATCH_SELECT', False):
    from django.test import TransactionTestCase
    from django.db.models.fields import FieldDoesNotExist
    from batch_select.models import Tag, Entry, Section, Batch
    from batch_select.replay import Replay
    from django import db
    import unittest
    
    def with_debug_true(fn):
        def _decorated(*arg, **kw):
            old_debug, settings.DEBUG = settings.DEBUG, True
            result = fn(*arg, **kw)
            settings.DEBUG = old_debug
            return result
        return _decorated
    
    class TestBatchSelect(TransactionTestCase):
        
        def test_batch_select_empty(self):
            entries = Entry.objects.batch_select('tags')
            self.failUnlessEqual([], list(entries))
        
        def test_batch_select_no_tags(self):
            entry = Entry.objects.create()
            entries = Entry.objects.batch_select('tags')
            self.failUnlessEqual([entry], list(entries))
        
        def _create_tags(self, *names):
            return [Tag.objects.create(name=name) for name in names]
        
        def _create_entries(self, count):
            return [Entry.objects.create() for _ in xrange(count)]
        
        def test_batch_select_default_name(self):
            entry = self._create_entries(1)[0]
            tag1, tag2 = self._create_tags('tag1', 'tag2')
            
            entry.tags.add(tag1, tag2)
            
            entry = Entry.objects.batch_select('tags')[0]
            
            self.failIf( getattr(entry, 'tags_all', None) is None )
            self.failUnlessEqual( set([tag1, tag2]), set(entry.tags_all) )
        
        def test_batch_select_non_default_name(self):
            entry = self._create_entries(1)[0]
            tag1, tag2 = self._create_tags('tag1', 'tag2')
            
            entry.tags.add(tag1, tag2)
            
            entry = Entry.objects.batch_select(batch_tags='tags')[0]
            
            self.failIf( getattr(entry, 'batch_tags', None) is None )
            self.failUnlessEqual( set([tag1, tag2]), set(entry.batch_tags) )
        
        def test_batch_select_with_tags(self):
            entry1, entry2, entry3, entry4 = self._create_entries(4)
            tag1, tag2, tag3 = self._create_tags('tag1', 'tag2', 'tag3')
            
            entry1.tags.add(tag1, tag2, tag3)
            
            entry2.tags.add(tag2)
            
            entry3.tags.add(tag2, tag3)
            
            entries = Entry.objects.batch_select('tags').order_by('id')
            entries = list(entries)
            
            self.failUnlessEqual([entry1, entry2, entry3, entry4], entries)
            
            entry1, entry2, entry3, entry4 = entries
            
            self.failUnlessEqual(set([tag1, tag2, tag3]), set(entry1.tags_all))
            self.failUnlessEqual(set([tag2]),             set(entry2.tags_all))
            self.failUnlessEqual(set([tag2, tag3]),       set(entry3.tags_all))
            self.failUnlessEqual(set([]),                 set(entry4.tags_all))

        def test_batch_select_filtering(self):
            entry1, entry2, entry3, entry4 = self._create_entries(4)
            tag1, tag2, tag3 = self._create_tags('tag1', 'tag2', 'tag3')
            
            entry1.tags.add(tag1, tag2, tag3)
            
            entry2.tags.add(tag2)
            
            entry3.tags.add(tag2, tag3)
            
            entries = Entry.objects.batch_select(Batch('tags', name='tag1')).order_by('id')
            entries = list(entries)
            
            self.failUnlessEqual([entry1, entry2, entry3, entry4], entries)
            
            entry1, entry2, entry3, entry4 = entries

            self.failUnlessEqual(set([tag1]), set(entry1.tags_all))
            self.failUnlessEqual(set([]),     set(entry2.tags_all))
            self.failUnlessEqual(set([]),     set(entry3.tags_all))
            self.failUnlessEqual(set([]),     set(entry4.tags_all))
        
        def test_batch_select_get(self):
            entry = Entry.objects.create()
            tag1, tag2, tag3 = self._create_tags('tag1', 'tag2', 'tag3')
            
            entry.tags.add(tag1, tag2, tag3)
            
            entry = Entry.objects.batch_select('tags').get()
            
            self.failIf( getattr(entry, 'tags_all', None) is None )
            self.failUnlessEqual( set([tag1, tag2, tag3]), set(entry.tags_all) )
        
        def test_batch_select_caching_works(self):
            # make sure that query set caching still
            # works and doesn't alter the added fields
            entry1, entry2, entry3, entry4 = self._create_entries(4)
            tag1, tag2, tag3 = self._create_tags('tag1', 'tag2', 'tag3')
            
            entry1.tags.add(tag1, tag2, tag3)
            
            entry2.tags.add(tag2)
            
            entry3.tags.add(tag2, tag3)
            
            qs = Entry.objects.batch_select(Batch('tags')).order_by('id')
            
            self.failUnlessEqual([entry1, entry2, entry3, entry4], list(qs))
            
            entry1, entry2, entry3, entry4 = list(qs)
            
            self.failUnlessEqual(set([tag1, tag2, tag3]), set(entry1.tags_all))
            self.failUnlessEqual(set([tag2]),             set(entry2.tags_all))
            self.failUnlessEqual(set([tag2, tag3]),       set(entry3.tags_all))
            self.failUnlessEqual(set([]),                 set(entry4.tags_all))
            
        def test_no_batch_select(self):
            # make sure things still work when we don't do a batch select
            entry1, entry2, entry3, entry4 = self._create_entries(4)
            
            qs = Entry.objects.all().order_by('id')
            
            self.failUnlessEqual([entry1, entry2, entry3, entry4], list(qs))
        
        def test_batch_select_after_new_query(self):
            entry1, entry2, entry3, entry4 = self._create_entries(4)
            tag1, tag2, tag3 = self._create_tags('tag1', 'tag2', 'tag3')
            
            entry1.tags.add(tag1, tag2, tag3)
            
            entry2.tags.add(tag2)
            
            entry3.tags.add(tag2, tag3)
            
            qs = Entry.objects.batch_select(Batch('tags')).order_by('id')
            
            self.failUnlessEqual([entry1, entry2, entry3, entry4], list(qs))
            
            entry1, entry2, entry3, entry4 = list(qs)
            
            self.failUnlessEqual(set([tag1, tag2, tag3]), set(entry1.tags_all))
            self.failUnlessEqual(set([tag2]),             set(entry2.tags_all))
            self.failUnlessEqual(set([tag2, tag3]),       set(entry3.tags_all))
            self.failUnlessEqual(set([]),                 set(entry4.tags_all))
            
            new_qs = qs.filter(id=entry1.id)
            
            self.failUnlessEqual([entry1], list(new_qs))
            
            entry1 = list(new_qs)[0]
            self.failUnlessEqual(set([tag1, tag2, tag3]), set(entry1.tags_all))
        
        @with_debug_true
        def test_batch_select_minimal_queries(self):
            # make sure we are only doing the number of sql queries we intend to
            entry1, entry2, entry3, entry4 = self._create_entries(4)
            tag1, tag2, tag3 = self._create_tags('tag1', 'tag2', 'tag3')
            
            entry1.tags.add(tag1, tag2, tag3)
            entry2.tags.add(tag2)
            entry3.tags.add(tag2, tag3)
            
            db.reset_queries()
            
            qs = Entry.objects.batch_select(Batch('tags')).order_by('id')
            
            self.failUnlessEqual([entry1, entry2, entry3, entry4], list(qs))
            
            # this should have resulted in only two queries
            self.failUnlessEqual(2, len(db.connection.queries))
            
            # double-check result is cached, and doesn't trigger more queries
            self.failUnlessEqual([entry1, entry2, entry3, entry4], list(qs))
            self.failUnlessEqual(2, len(db.connection.queries))
        
        @with_debug_true
        def test_no_batch_select_minimal_queries(self):
            # check we haven't altered the original querying behaviour
            entry1, entry2, entry3 = self._create_entries(3)
            
            db.reset_queries()

            qs = Entry.objects.order_by('id')

            self.failUnlessEqual([entry1, entry2, entry3], list(qs))

            # this should have resulted in only two queries
            self.failUnlessEqual(1, len(db.connection.queries))
            
            # check caching still works
            self.failUnlessEqual([entry1, entry2, entry3], list(qs))
            self.failUnlessEqual(1, len(db.connection.queries))
        
        def test_batch_select_non_existant_field(self):
            try:
                qs = Entry.objects.batch_select(Batch('qwerty')).order_by('id')
                self.fail('selected field that does not exist')
            except FieldDoesNotExist:
                pass
        
        def test_batch_select_non_m2m_field(self):
            try:
                qs = Entry.objects.batch_select(Batch('title')).order_by('id')
                self.fail('selected field that is not m2m field')
            except FieldDoesNotExist:
                pass
        
        def test_batch_select_empty_one_to_many(self):
            sections = Section.objects.batch_select('entry')
            self.failUnlessEqual([], list(sections))
        
        def test_batch_select_one_to_many_no_children(self):
            section1 = Section.objects.create(name='s1')
            section2 = Section.objects.create(name='s2')
            
            sections = Section.objects.batch_select('entry').order_by('id')
            self.failUnlessEqual([section1, section2], list(sections))
        
        def test_batch_select_one_to_many_with_children(self):
            section1 = Section.objects.create(name='s1')
            section2 = Section.objects.create(name='s2')
            section3 = Section.objects.create(name='s3')
            
            entry1 = Entry.objects.create(section=section1)
            entry2 = Entry.objects.create(section=section1)
            entry3 = Entry.objects.create(section=section3)
            
            sections = Section.objects.batch_select('entry').order_by('id')
            self.failUnlessEqual([section1, section2, section3], list(sections))
            
            section1, section2, section3 = list(sections)
            
            self.failUnlessEqual(set([entry1, entry2]), set(section1.entry_all))
            self.failUnlessEqual(set([]),               set(section2.entry_all))
            self.failUnlessEqual(set([entry3]),         set(section3.entry_all))
        
        @with_debug_true
        def test_batch_select_one_to_many_with_children_minimal_queries(self):
            section1 = Section.objects.create(name='s1')
            section2 = Section.objects.create(name='s2')
            section3 = Section.objects.create(name='s3')
            
            entry1 = Entry.objects.create(section=section1)
            entry2 = Entry.objects.create(section=section2)
            entry3 = Entry.objects.create(section=section3)
            
            db.reset_queries()
            
            sections = Section.objects.batch_select('entry').order_by('id')
            self.failUnlessEqual([section1, section2, section3], list(sections))
            
            # this should have resulted in only two queries
            self.failUnlessEqual(2, len(db.connection.queries))
            
            section1, section2, section3 = list(sections)
            
            self.failUnlessEqual(set([entry1]), set(section1.entry_all))
            self.failUnlessEqual(set([entry2]), set(section2.entry_all))
            self.failUnlessEqual(set([entry3]), set(section3.entry_all))
    
    class ReplayTestCase(unittest.TestCase):
        
        def setUp(self):
            class ReplayTest(Replay):
                __replayable__ = ('lower', 'upper', 'replace')
            self.klass = ReplayTest
            self.instance = ReplayTest()
        
        def test_replayable_methods_present_on_class(self):
            self.failIf( getattr(self.klass, 'lower', None) is None )
            self.failIf( getattr(self.klass, 'upper', None) is None )
            self.failIf( getattr(self.klass, 'replace', None) is None )
        
        def test_replayable_methods_present_on_instance(self):
            self.failIf( getattr(self.instance, 'lower', None) is None )
            self.failIf( getattr(self.instance, 'upper', None) is None )
            self.failIf( getattr(self.instance, 'replace', None) is None )
        
        def test_replay_methods_recorded(self):
            r = self.instance
            self.failUnlessEqual([], r._replays)
            
            self.failIf(r == r.upper())
            
            self.failUnlessEqual([('upper', (), {})], r.upper()._replays)
            self.failUnlessEqual([('lower', (), {})], r.lower()._replays)
            self.failUnlessEqual([('replace', (), {})], r.replace()._replays)
            
            self.failUnlessEqual([('upper', (1,), {})], r.upper(1)._replays)
            self.failUnlessEqual([('upper', (1,), {'param': 's'})], r.upper(1, param='s')._replays)
            
            self.failUnlessEqual([('upper', (), {'name__contains': 'test'}),
                                  ('replace', ('id',), {})],
                                 r.upper(name__contains='test').replace('id')._replays)
        
        def test_replay_no_replay(self):
            r = self.instance
            s = 'gfjhGF&'
            self.failUnlessEqual(s, r.replay(s))
        
        def test_replay_single_call(self):
            r = self.instance.upper()
            self.failUnlessEqual('MYWORD', r.replay('MyWord'))
            
            r = self.instance.lower()
            self.failUnlessEqual('myword', r.replay('MyWord'))
            
            r = self.instance.replace('a', 'b')
            self.failUnlessEqual('bbb', r.replay('aaa'))
            
            r = self.instance.replace('a', 'b', 1)
            self.failUnlessEqual('baa', r.replay('aaa'))
            
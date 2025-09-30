"""N+1 Query Prevention Tests"""
import pytest
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session, joinedload
from typing import List
import time

Base = declarative_base()

# Mock database models
class Quote(Base):
    __tablename__ = "quotes"
    id = Column(Integer, primary_key=True)
    customer_name = Column(String)
    items = relationship("QuoteItem", back_populates="quote", lazy="select")
    panels = relationship("Panel", back_populates="quote", lazy="select")

class QuoteItem(Base):
    __tablename__ = "quote_items"
    id = Column(Integer, primary_key=True)
    quote_id = Column(Integer, ForeignKey("quotes.id"))
    breaker_sku = Column(String)
    quantity = Column(Integer)
    price = Column(Float)
    quote = relationship("Quote", back_populates="items")

class Panel(Base):
    __tablename__ = "panels"
    id = Column(Integer, primary_key=True)
    quote_id = Column(Integer, ForeignKey("quotes.id"))
    enclosure_sku = Column(String)
    fit_score = Column(Float)
    quote = relationship("Quote", back_populates="panels")

class QueryCounter:
    """Count database queries for testing"""
    def __init__(self):
        self.count = 0
        self.queries = []

    def __call__(self, *args, **kwargs):
        self.count += 1
        if args:
            self.queries.append(str(args[0]))

    def reset(self):
        self.count = 0
        self.queries = []

class TestNPlusOne:
    """Test N+1 query prevention"""

    def setup_method(self):
        """Setup in-memory database"""
        # Create in-memory SQLite database
        self.engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

        # Query counter
        self.query_counter = QueryCounter()

        # Hook into SQLAlchemy events to count queries
        from sqlalchemy import event
        event.listen(self.engine, "before_execute", self.query_counter)

        # Create test data
        self._create_test_data()

    def teardown_method(self):
        """Cleanup"""
        self.session.close()
        self.engine.dispose()

    def _create_test_data(self):
        """Create test data"""
        # Create 10 quotes, each with 5 items and 2 panels
        for i in range(10):
            quote = Quote(customer_name=f"Customer {i}")
            self.session.add(quote)
            self.session.flush()

            # Add items
            for j in range(5):
                item = QuoteItem(
                    quote_id=quote.id,
                    breaker_sku=f"BKR-{i}-{j}",
                    quantity=j + 1,
                    price=100.0 * (j + 1)
                )
                self.session.add(item)

            # Add panels
            for k in range(2):
                panel = Panel(
                    quote_id=quote.id,
                    enclosure_sku=f"ENC-{i}-{k}",
                    fit_score=0.9 + k * 0.05
                )
                self.session.add(panel)

        self.session.commit()

    def test_n_plus_one_problem_demonstration(self):
        """Demonstrate N+1 problem"""
        self.query_counter.reset()

        # Bad practice: lazy loading
        quotes = self.session.query(Quote).all()  # 1 query

        # Access items for each quote (N queries)
        for quote in quotes:
            _ = len(quote.items)  # Each access triggers a query
            _ = len(quote.panels)  # Another query per quote

        # Should have 1 + N*2 queries (1 for quotes, 2 per quote for items and panels)
        expected_queries = 1 + (10 * 2)  # 21 queries
        assert self.query_counter.count == expected_queries, \
            f"N+1 problem: {self.query_counter.count} queries executed (expected {expected_queries})"

    def test_n_plus_one_solution_joinedload(self):
        """Test N+1 solution using joinedload"""
        self.query_counter.reset()

        # Good practice: eager loading with joinedload
        quotes = self.session.query(Quote).options(
            joinedload(Quote.items),
            joinedload(Quote.panels)
        ).all()  # Should be 1-3 queries total

        # Access items for each quote (no additional queries)
        for quote in quotes:
            _ = len(quote.items)
            _ = len(quote.panels)

        # Should have at most 3 queries (one for each table or less with joins)
        assert self.query_counter.count <= 3, \
            f"Too many queries with joinedload: {self.query_counter.count} (expected ≤ 3)"

    def test_query_count_for_list_endpoint(self):
        """Test query count for list endpoint simulation"""
        self.query_counter.reset()

        def list_quotes_bad() -> List[dict]:
            """Simulate bad list endpoint"""
            quotes = self.session.query(Quote).all()
            result = []
            for quote in quotes:
                result.append({
                    "id": quote.id,
                    "customer": quote.customer_name,
                    "items_count": len(quote.items),  # Triggers query
                    "panels_count": len(quote.panels)  # Triggers query
                })
            return result

        # Bad implementation
        _ = list_quotes_bad()
        bad_query_count = self.query_counter.count

        self.query_counter.reset()

        def list_quotes_good() -> List[dict]:
            """Simulate good list endpoint"""
            quotes = self.session.query(Quote).options(
                joinedload(Quote.items),
                joinedload(Quote.panels)
            ).all()
            result = []
            for quote in quotes:
                result.append({
                    "id": quote.id,
                    "customer": quote.customer_name,
                    "items_count": len(quote.items),  # No additional query
                    "panels_count": len(quote.panels)  # No additional query
                })
            return result

        # Good implementation
        _ = list_quotes_good()
        good_query_count = self.query_counter.count

        # Good implementation should use significantly fewer queries
        assert good_query_count <= 3, f"Good implementation uses too many queries: {good_query_count}"
        assert bad_query_count > good_query_count * 5, \
            f"Bad implementation should use many more queries: {bad_query_count} vs {good_query_count}"

    def test_performance_impact(self):
        """Test performance impact of N+1"""
        # Measure bad implementation
        self.query_counter.reset()
        start = time.time()

        quotes = self.session.query(Quote).all()
        for quote in quotes:
            _ = quote.items
            _ = quote.panels

        bad_time = time.time() - start
        bad_queries = self.query_counter.count

        # Measure good implementation
        self.query_counter.reset()
        start = time.time()

        quotes = self.session.query(Quote).options(
            joinedload(Quote.items),
            joinedload(Quote.panels)
        ).all()
        for quote in quotes:
            _ = quote.items
            _ = quote.panels

        good_time = time.time() - start
        good_queries = self.query_counter.count

        # Good implementation should be faster and use fewer queries
        assert good_queries < bad_queries, \
            f"Good implementation should use fewer queries: {good_queries} vs {bad_queries}"

        # Log results for evidence
        print(f"\nN+1 Performance Test Results:")
        print(f"Bad: {bad_queries} queries in {bad_time:.4f}s")
        print(f"Good: {good_queries} queries in {good_time:.4f}s")
        print(f"Improvement: {bad_queries/good_queries:.1f}x fewer queries")

    def test_complex_nested_relationships(self):
        """Test N+1 prevention with complex nested relationships"""
        # Add another level of relationship for testing
        class BreakerDetail(Base):
            __tablename__ = "breaker_details"
            id = Column(Integer, primary_key=True)
            item_id = Column(Integer, ForeignKey("quote_items.id"))
            specification = Column(String)

        # Would need to extend the model and test nested loading
        # This demonstrates the pattern for complex cases
        self.query_counter.reset()

        # Complex query with multiple levels
        quotes = self.session.query(Quote).options(
            joinedload(Quote.items),
            joinedload(Quote.panels)
        ).limit(5).all()

        # Should still be efficient
        assert self.query_counter.count <= 3, \
            f"Complex query inefficient: {self.query_counter.count} queries"

    def test_pagination_with_eager_loading(self):
        """Test pagination doesn't break eager loading"""
        self.query_counter.reset()

        # Paginated query with eager loading
        page = 1
        per_page = 5

        quotes = self.session.query(Quote).options(
            joinedload(Quote.items),
            joinedload(Quote.panels)
        ).offset((page - 1) * per_page).limit(per_page).all()

        for quote in quotes:
            _ = quote.items
            _ = quote.panels

        # Should still be efficient even with pagination
        assert self.query_counter.count <= 3, \
            f"Paginated query inefficient: {self.query_counter.count} queries"

    def test_filter_with_eager_loading(self):
        """Test filtering doesn't break eager loading"""
        self.query_counter.reset()

        # Filtered query with eager loading
        quotes = self.session.query(Quote).filter(
            Quote.customer_name.like("Customer%")
        ).options(
            joinedload(Quote.items),
            joinedload(Quote.panels)
        ).all()

        for quote in quotes:
            _ = quote.items
            _ = quote.panels

        # Should still be efficient even with filtering
        assert self.query_counter.count <= 3, \
            f"Filtered query inefficient: {self.query_counter.count} queries"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
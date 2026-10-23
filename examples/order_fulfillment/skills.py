"""Runtime Skills from the 2.1.3 public API; every capability is owned explicitly by its Agent."""
import agentic_systems as toolkit
from . import tools

intake = toolkit.skill(name="intake", tools=[tools.normalize_order, tools.validate_order])
pricing = toolkit.skill(name="pricing", tools=[tools.price_order])
inventory = toolkit.skill(name="inventory", tools=[tools.check_inventory])
policy = toolkit.skill(name="policy", tools=[tools.assess_policy])
approval = toolkit.skill(name="approval", tools=[tools.approve_order])
review = toolkit.skill(name="review", tools=[tools.review_order])
rejection = toolkit.skill(name="rejection", tools=[tools.reject_order])

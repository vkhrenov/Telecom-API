import logging

from sqlalchemy import select, delete
from src.models.users import RatesModel, ProductsModel, EndpointsModel, UserSettingsModel
from src.logic.utilities import normalize_date_for_pg, normalize_str_date, normalize_str_expdate
from datetime import datetime

logger = logging.getLogger(__name__)

# Function to get a list of products with pagination -----------------------------------------------------------
async def get_product_list(session, range_from=0, range_to=24, filter_dict={}, sort_list=[]):

    query = select(ProductsModel)

    # Apply sorting if sort_list is provided
    # sort_list example: ["username", "ASC"]
    if sort_list and isinstance(sort_list, list) and len(sort_list) == 2:
        field_name, order = sort_list
        field = getattr(ProductsModel, field_name, None)
       
        if field is not None:
            if order.upper() == "ASC":
                query = query.order_by(field.asc())
            elif order.upper() == "DESC":
                query = query.order_by(field.desc())

    if filter_dict and isinstance(filter_dict, dict):
        for field_name, value in filter_dict.items():
            field = getattr(ProductsModel, field_name, None)
            
            if field == ProductsModel.id:
                ids = set()
                if isinstance(value, (list, tuple, set)):
                    candidates = value
                elif isinstance(value, str):
                    candidates = [v.strip() for v in value.split(",") if v.strip()]
                else:
                    candidates = [value]

                for v in candidates:
                    try:
                        ids.add(int(v))
                    except (ValueError, TypeError):
                        # skip non-integer candidates
                        continue

                if ids:
                    query = query.where(ProductsModel.id.in_(ids))
 
                continue
            else:    
                if field is not None and value:
                    query = query.where(field.ilike(f"%{value}%"))

    result = await session.execute(query)
    ret = result.all()
    total_count = len(ret)

    # Apply pagination
    paginated_ret = ret[range_from:range_to + 1]

    # Prepare data for response
    data = [
        { 
            "id": row[0].id,
            "productname": row[0].productname,
            "description": row[0].description
        }
        for row in paginated_ret
    ]

    return {
        "data": data,
        "total": total_count
    }

# Function to get a single product by ID -------------------------------------------------------------------------------
async def get_product(session, product_id):

    result = await session.execute(
        select(ProductsModel)
        .where(ProductsModel.id == product_id)
    )
    ret = result.first()

    if not ret:
        return {"error": "Product not found"}

    product = ret[0]

    # join EndpointsModel to order by endpoint name
    query = (
        select(RatesModel)
        .join(EndpointsModel, RatesModel.endpointid == EndpointsModel.id)
        .where(RatesModel.productid == product_id)
        .order_by(EndpointsModel.endpoint.asc())
    )
    result = await session.execute(query)
    ret = result.all()
    rates = [
        {
            "id": row[0].id,
            "endpointid": row[0].endpointid,
            "rate": row[0].rate,
            "dateeff": normalize_str_date(str(row[0].dateeff)) if row[0].dateeff is not None else None,
            "dateexp": normalize_str_expdate(str(row[0].dateexp)) if row[0].dateexp is not None else None
        }
        for row in ret
    ]

    return {
        "id": product.id,
        "productname": product.productname,
        "description": product.description,
        "rates": rates
    }

# Function to create a new product -------------------------------------------------------------------------------
async def create_product(session, product_data):

    new_product = ProductsModel(
        productname=product_data.get("productname"),
        description=product_data.get("description")
    )

    session.add(new_product)
    await session.commit()
    await session.refresh(new_product)
    return {
        "id": new_product.id,
        "productname": new_product.productname,
        "description": new_product.description
    }

# Function to update an existing product by ID -------------------------------------------------------------------------------
async def update_productid(session, product_id, product_data):  

    # Fetch existing product
    existing_product = await session.get(ProductsModel, product_id)
    if not existing_product:
       return {"error": "Product not found"}
 
    # update fields if they exist in product_data
    for field in ["productname", "description"]:
        if field in product_data:
            setattr(existing_product, field, product_data[field])

    if "rates" in product_data:
        result = await session.execute(
            select(RatesModel.id)
            .where(RatesModel.productid == product_id)
        )
        existing_ids = {row[0] for row in result.all()}
        incoming_ids = set()

        # Update rates
        for rate_data in product_data["rates"]:
            rate_id = rate_data.get("id")
            rate_data["dateeff"] = normalize_date_for_pg(rate_data["dateeff"])
            if rate_data["dateexp"] == "" or rate_data["dateexp"] is None:
                rate_data["dateexp"] = datetime(2222, 1, 1, 0, 0, 0)
            else:
                rate_data["dateexp"]=normalize_date_for_pg(rate_data["dateexp"])

            if rate_id:
                incoming_ids.add(rate_id)
                existing_rate = await session.get(RatesModel, rate_id)
                if existing_rate:
                    for field in ["endpointid", "rate", "dateeff", "dateexp"]:
                        if field in rate_data:
                            setattr(existing_rate, field, rate_data[field])
            else:
                new_rate = RatesModel(
                    productid=product_id,
                    endpointid=rate_data.get("endpointid"),
                    rate=rate_data.get("rate"),
                    dateeff=rate_data.get("dateeff"),
                    dateexp=rate_data.get("dateexp")
                )
                session.add(new_rate)

        # Remove existing rates not in incoming data
        ids_to_delete = list(existing_ids - incoming_ids)
        if ids_to_delete:
            await session.execute(
                delete(RatesModel).where(RatesModel.id.in_(ids_to_delete))
            )

    session.add(existing_product)
    await session.commit()
    await session.refresh(existing_product)

    return {
        "id": existing_product.id,
        "productname": existing_product.productname,
        "description": existing_product.description 
    }

# Function to delete a product by ID -------------------------------------------------------------------------------
async def delete_productid(session, product_id):  

    result = await session.execute(
        select(ProductsModel)
        .where(ProductsModel.id == product_id)
    )
    ret = result.first()

    if not ret:
        return {"error": "Product not found"}

    product = ret[0]

    # Check if a product assigned to any users
    result = await session.execute(
        select(UserSettingsModel)
        .where(UserSettingsModel.productid == product_id)
    )
    ret = result.first()
    if ret:
        return  {"error" : "Cannot delete product assigned to users"}

    # Delete associated rates in one DB call, then delete product
    await session.execute(delete(RatesModel).where(RatesModel.productid == product_id))
    await session.execute(delete(ProductsModel).where(ProductsModel.id == product_id))
    await session.commit()

    return {
        "id": product.id,
        "productname": product.productname,
        "description": product.description 
    }
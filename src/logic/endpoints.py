import os

from sqlalchemy import select, delete
from src.models.users import EndpointsModel

# Function to get a list of endpoints with pagination -----------------------------------------------------------
async def get_endpoint_list(session, range_from=0, range_to=24, filter_dict={}, sort_list=[]):

    query = select(EndpointsModel)

    # Apply sorting if sort_list is provided
    # sort_list example: ["username", "ASC"]
    if sort_list and isinstance(sort_list, list) and len(sort_list) == 2:
        field_name, order = sort_list
        field = getattr(EndpointsModel, field_name, None)
       
        if field is not None:
            if order.upper() == "ASC":
                query = query.order_by(field.asc())
            elif order.upper() == "DESC":
                query = query.order_by(field.desc())

    if filter_dict and isinstance(filter_dict, dict):
        for field_name, value in filter_dict.items():
            field = getattr(EndpointsModel, field_name, None)
            
            if field == EndpointsModel.id:
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
                    query = query.where(EndpointsModel.id.in_(ids))
 
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
            "endpoint": row[0].endpoint,
            "description": row[0].description
        }
        for row in paginated_ret
    ]

    return {
        "data": data,
        "total": total_count
    }

# Function to get a single endpoint by ID -------------------------------------------------------------------------------
async def get_endpoint(session, endpoint_id):

    result = await session.execute(
        select(EndpointsModel)
        .where(EndpointsModel.id == endpoint_id)
    )
    ret = result.first()

    if not ret:
        return {"error": "Endpoint not found"}

    endpoint = ret[0]

    return {
        "id": endpoint.id,
        "endpoint": endpoint.endpoint,
        "description": endpoint.description
    }

# Function to create a new endpoint -------------------------------------------------------------------------------
async def create_endpoint(session, endpoint_data):

    new_endpoint = EndpointsModel(
        endpoint = endpoint_data.get("endpoint"),
        description = endpoint_data.get("description")
    )

    session.add(new_endpoint)
    await session.commit()
    await session.refresh(new_endpoint)
    return {
        "id": new_endpoint.id,
        "endpoint": new_endpoint.endpoint,
        "description": new_endpoint.description
    }

# Function to update an existing endpoint by ID -------------------------------------------------------------------------------
async def update_endpointid(session, endpoint_id, endpoint_data):  

    # Fetch existing endpoint
    existing_endpoint = await session.get(EndpointsModel, endpoint_id)
    if not existing_endpoint:
       return {"error": "Endpoint not found"}
 
    # update fields if they exist in endpoint_data
    for field in ["endpoint", "description"]:
        if field in endpoint_data:
            setattr(existing_endpoint, field, endpoint_data[field])

    session.add(existing_endpoint)
    await session.commit()
    await session.refresh(existing_endpoint)

    return {
        "id": existing_endpoint.id,
        "endpoint": existing_endpoint.endpoint,
        "description": existing_endpoint.description 
    }

# Function to delete an endpoint by ID -------------------------------------------------------------------------------
async def delete_endpointid(session, endpoint_id):  

    result = await session.execute(
        select(EndpointsModel)
        .where(EndpointsModel.id == endpoint_id)
    )
    ret = result.first()

    if not ret:
        return {"error": "Endpoint not found"}

    endpoint = ret[0]

    await session.execute(delete(EndpointsModel).where(EndpointsModel.id == endpoint_id))
    await session.commit()

    return {
        "id": endpoint.id,
        "endpoint": endpoint.endpoint,
        "description": endpoint.description 
    }
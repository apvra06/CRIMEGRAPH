from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException

from app.schemas import GraphResponse, ShortestPathRequest, ShortestPathResponse, PersonDetail
from app.services import graph_service

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/data", response_model=GraphResponse)
def get_graph(
    view_mode: str = Query("Whole network", description="Whole network, Specific person, Specific community"),
    person: Optional[str] = Query(None, description="Person name when view_mode is 'Specific person'"),
    community: Optional[int] = Query(None, description="Community ID when view_mode is 'Specific community'"),
    start_date: Optional[str] = Query(None, description="YYYY-MM-DD start filter"),
    end_date: Optional[str] = Query(None, description="YYYY-MM-DD end filter"),
    people_only: bool = Query(False, description="Whether to filter out non-person entities"),
    color_by: str = Query("Entity type", description="'Entity type' or 'Community'")
):
    return graph_service.get_graph_data(
        view_mode=view_mode,
        selected_person=person,
        selected_comm=community,
        start_date=start_date,
        end_date=end_date,
        people_only=people_only,
        color_by=color_by
    )


@router.get("/people", response_model=List[str])
def get_people():
    return graph_service.get_people_names()


@router.get("/communities", response_model=List[int])
def get_communities():
    return graph_service.get_communities_list()


@router.get("/date-range")
def get_date_range():
    start, end = graph_service.get_date_range()
    return {"start_date": start, "end_date": end}


@router.get("/person/{name}", response_model=PersonDetail)
def get_person_detail(name: str):
    detail = graph_service.get_person_detail(name)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Person '{name}' not found")
    return detail


@router.post("/shortest-path", response_model=ShortestPathResponse)
def compute_shortest_path(body: ShortestPathRequest):
    nodes, edges, error = graph_service.find_shortest_path(body.p1, body.p2)
    return ShortestPathResponse(
        found=len(nodes) > 0,
        path_nodes=nodes,
        path_edges=edges,
        message=error if not nodes else f"Connection path established ({len(nodes)} hops)"
    )

